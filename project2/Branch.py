import json
import multiprocessing
import sys
import time
from concurrent import futures
import logging
import datetime

import grpc
import distributed_banking_system_pb2
import distributed_banking_system_pb2_grpc

_ONE_DAY = datetime.timedelta(days=1)


class Branch(distributed_banking_system_pb2_grpc.BankingServiceServicer):

    def __init__(self, id, balance, branches):
        # unique ID of the Branch
        self.id = id
        # replica of the Branch's balance
        self.balance = balance
        # the list of process IDs of the branches
        self.branches = branches
        # the list of Client stubs to communicate with the branches
        self.stubList = list()
        # a list of received messages used for debugging purpose
        self.recvMsg = list()
        # iterate the processID of the branches
        self.branch_id_list = list()
        self.initialize_stubs()
        # logical clock
        self.logical_clock = 0

    def update_logical_clock(self, event_ts):
        self.logical_clock = 1 + max(self.logical_clock, event_ts)

    def increment_logical_clock(self):
        self.logical_clock += 1

    def initialize_stubs(self):
        # Initialize gRPC stubs for communication with other branches
        for branch_id in self.branches:
            if branch_id != self.id:
                port = str(50050 + int(branch_id))
                address = f"localhost:{port}"
                channel = grpc.insecure_channel(address)
                stub = distributed_banking_system_pb2_grpc.BankingServiceStub(channel)
                self.stubList.append(stub)

    def record_event_reception(self, request):
        customer_request = request.customer_requests[0]
        self.update_logical_clock(customer_request.logical_clock)
        event = {"id": self.id,
                 "customer_request_id": customer_request.customer_request_id,
                 "type": "branch",
                 "logical_clock": self.logical_clock,
                 "interface": customer_request.interface,
                 "comment": f"event_received from {request.type} {request.id}"}
        return event

    def MsgDelivery(self, request, context):
        type = request.type
        response = [self.record_event_reception(request)]

        match type:
            case "customer":
                response.extend(self.process_customer_events(request))
            case "branch":
                self.process_branch_events(request)

        return distributed_banking_system_pb2.BankingOperationResponse(event_result=response)

    def process_customer_events(self, request):
        response = list()
        replica_branch_responses = list()
        id = request.id
        type = request.type
        for customer_request in request.customer_requests:
            match customer_request.interface:
                case "query":
                    pass
                    # response.append(self.query(customer_request, id, type))
                case "deposit":
                    deposit_response, propagate_deposit_response = self.deposit(customer_request, id, type)
                    response.append(deposit_response)
                    replica_branch_responses.extend(propagate_deposit_response)
                case "withdraw":
                    withdraw_response, propagate_withdraw_response = self.withdraw(customer_request, id, type)
                    response.append(withdraw_response)
                    replica_branch_responses.extend(propagate_withdraw_response)

        replica_branch_dict_responses = []
        # for replica_branch_response in replica_branch_responses:
        #     replica_branch_dict_responses.append(protobuf_to_dict(replica_branch_response))

        self.recvMsg.extend(replica_branch_dict_responses)
        print(replica_branch_responses)
        return replica_branch_responses

    def query(self, request, id, type):
        return {'interface': 'query', 'result': None, 'balance': self.balance}

    def deposit(self, customer_request, id, type):
        # result = "failed"
        replica_branch_responses = []
        try:
            replica_branch_responses = self.replicate_deposit(customer_request)
            self.balance += customer_request.money
            # result = "success"
        except Exception as e:
            print(e)
            # result = "failed"
            replica_branch_responses = []
        response = {"id": id,
                    "customer_request_id": customer_request.customer_request_id,
                    "type": "branch",
                    "logical_clock": self.logical_clock,
                    "interface": customer_request.interface,
                    "comment": f"event_sent to {type} {id}"}
        return response, replica_branch_responses

    def withdraw(self, customer_request, id, type):
        result = "failed"
        replica_branch_responses = []
        try:
            if self.balance >= customer_request.money:
                replica_branch_responses = self.replicate_withdraw(customer_request)
                self.balance -= customer_request.money
                result = "success"
        except  Exception as e:
            print(e)
            result = "failed"
            replica_branch_responses = []
        response = {'interface': 'withdraw', 'result': result}
        return response, replica_branch_responses

    def process_branch_events(self, request):
        response = list()
        for event in request.customer_requests:
            match event.interface:
                case "withdraw":
                    response.append(self.propagate_withdraw(event))
                case "deposit":
                    response.append(self.propagate_deposit(event))
        return response

    def propagate_deposit(self, event):
        self.balance += event.money
        return {'interface': 'propagate_deposit', 'result': 'success'}

    def propagate_withdraw(self, request):
        self.balance -= request.money
        return {'interface': 'propagate_withdraw', 'result': 'success'}

    def replicate_deposit(self, customer_request):
        replica_branch_responses = []
        for id, stub in enumerate(self.stubList, 1):
            if id >= self.id:
                id += 1
            self.increment_logical_clock()
            customer_request.logical_clock = self.logical_clock
            customer_request.interface = "propagate_deposit"

            event_ack = {"id": self.id,
                         "customer_request_id": customer_request.customer_request_id,
                         "type": "branch",
                         "logical_clock": self.logical_clock,
                         "interface": "propagate_deposit",
                         "comment": f"event_sent to branch {id}"}
            replica_branch_responses.append(event_ack)
            replica_branch_response = stub.MsgDelivery(
                distributed_banking_system_pb2.BankingOperationRequest(id=self.id, type="branch",
                                                                       customer_requests=[customer_request]))
            dict_response = protobuf_to_dict(replica_branch_response)
            replica_branch_responses.extend(dict_response["event_result"])
            # if response.recv[0].result != "success":
            #     print(f"Failed to replicate deposit to branch {self.stubList.index(stub) + 1}")
            # replica_branch_responses.append(response)
        return replica_branch_responses

    def replicate_withdraw(self, customer_request):
        replica_branch_responses = []
        for id, stub in enumerate(self.stubList, 1):
            if id >= self.id:
                id += 1
            self.increment_logical_clock()
            customer_request.logical_clock = self.logical_clock
            customer_request.interface = "propagate_withdraw"
            event_ack = {"id": self.id,
                         "customer_request_id": customer_request.customer_request_id,
                         "type": "branch",
                         "logical_clock": self.logical_clock,
                         "interface": "propagate_withdraw",
                         "comment": f"event_sent to branch {id}"}
            replica_branch_responses.append(event_ack)
            replica_branch_response=stub.MsgDelivery(
                distributed_banking_system_pb2.BankingOperationRequest(id=self.id, type="branch",
                                                                       customer_requests=[customer_request]))
            dict_response=protobuf_to_dict(replica_branch_response)
            replica_branch_responses.extend(dict_response["event_result"])
            # if response.recv[0].result != "success":
            #     print(f"Failed to replicate withdrawal to branch {self.stubList.index(stub) + 1}")
            # replica_branch_responses.append(response)
        return replica_branch_responses


def serve(port, id, balance, branch_id_list, result_queue):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    distributed_banking_system_pb2_grpc.add_BankingServiceServicer_to_server(Branch(id, balance, branch_id_list),
                                                                             server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    print("Server started, listening on " + port)
    wait_for_termination(server)
    result_queue.put(server)


def wait_for_termination(server):
    try:
        while True:
            time.sleep(_ONE_DAY.total_seconds())
    except KeyboardInterrupt:
        server.stop(None)


def initialize_branch_servers(branch_id_list):
    input_file_path = get_input_file_path()
    try:
        # Open and read the JSON file
        with open(input_file_path, 'r') as json_file:
            # Parse JSON data into a Python list of dictionaries
            parsed_data = json.load(json_file)

        processes = []
        result_queue = multiprocessing.Queue()
        # Now, `parsed_data` is a Python list containing dictionaries
        for item in parsed_data:
            if item["type"] != "branch":
                continue

            id = item["id"]
            type = item["type"]
            balance = item["balance"]
            # print("ID:", item["id"])
            # print("Type:", item["type"])
            # print("Balance:", item["balance"])

            process = multiprocessing.Process(target=serve,
                                              args=(str(50050 + int(id)), id, balance, branch_id_list, result_queue))
            processes.append(process)
            process.start()

        # Wait for all server processes to finish
        for process in processes:
            process.join()

    except FileNotFoundError:
        print(f"File not found: {input_file_path}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def get_input_file_path():
    if len(sys.argv) != 2:
        input_file_path = "./Input/input.json"
    else:
        input_file_path = sys.argv[1]
    return input_file_path


def populate_branch_id_list(branch_id_list):
    input_file_path = get_input_file_path()
    try:
        # Open and read the JSON file
        with open(input_file_path, 'r') as json_file:
            # Parse JSON data into a Python list of dictionaries
            parsed_data = json.load(json_file)
            for item in parsed_data:
                if item["type"] != "branch":
                    continue
                branch_id_list.append(item["id"])
    except FileNotFoundError:
        print(f"File not found: {input_file_path}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def protobuf_to_dict(message):
    result = {}
    for field, value in message.ListFields():
        if field.type == field.TYPE_MESSAGE:
            if field.label == field.LABEL_REPEATED:
                result[field.name] = [protobuf_to_dict(item) for item in value]
            else:
                result[field.name] = protobuf_to_dict(value)
        else:
            result[field.name] = value
    return result


if __name__ == "__main__":
    logging.basicConfig()
    branch_id_list = []
    populate_branch_id_list(branch_id_list)
    initialize_branch_servers(branch_id_list)
