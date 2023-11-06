import multiprocessing
import os
import sys

import grpc
import distributed_banking_system_pb2
import distributed_banking_system_pb2_grpc
import json
import time

OUTPUT_FILE_PATH = "./Output/output.json"


def dict_to_str(response):
    return str(protobuf_to_dict(response)) + "\n"


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


class Customer:
    def __init__(self, id, events):
        # unique ID of the Customer
        self.id = id
        # events from the input
        self.events = events
        # a list of received messages used for debugging purpose
        self.recvMsg = list()
        # pointer for the stub
        self.stub = self.createStub()

    def createStub(self):
        port = str(50050 + int(id))

        address = f"localhost:{port}"
        channel = grpc.insecure_channel(address)
        return distributed_banking_system_pb2_grpc.BankingServiceStub(channel)


    def executeEvents(self):
        banking_service_stub = self.stub
        events = self.events
        id = self.id
        response = banking_service_stub.MsgDelivery(
            distributed_banking_system_pb2.BankingOperationRequest(id=id, type="customer", events=events))
        return response

    def update_recvMsg(self, branch_response):
        branch_dict_response = protobuf_to_dict(branch_response)
        self.recvMsg.append(branch_dict_response)
        print(branch_dict_response)


def start_customer_process(id, events):
    customer = Customer(id, events)
    branch_response = customer.executeEvents()
    customer.update_recvMsg(branch_response)

    directory = os.path.dirname(OUTPUT_FILE_PATH)
    if not os.path.exists(directory):
        os.makedirs(directory)

    output_file = open(OUTPUT_FILE_PATH, "a")
    output_file.write(dict_to_str(branch_response))
    output_file.close()


if __name__ == '__main__':
    res = []
    if len(sys.argv) != 2:
        input_file_path = "./Input/input.json"
    else:
        input_file_path = sys.argv[1]

    try:
        # Open and read the JSON file
        input_file = open(input_file_path, 'r')
        # Parse JSON data into a Python list of dictionaries
        processes = []
        result_queue = multiprocessing.Queue()
        parsed_data = json.load(input_file)
        for item in parsed_data:
            if item["type"] != "customer":
                continue

            id = item["id"]
            type = item["type"]
            events = item["events"]
            # print("ID:", item["id"])
            # print("Type:", item["type"])
            # print("Events:", item["events"])
            process = multiprocessing.Process(target=start_customer_process,
                                              args=(id, events))
            processes.append(process)
            process.start()

            # sleep for 3 seconds for event propagation
            time.sleep(3)
        for process in processes:
            process.join()
        print("Customer process completed\n")
    except FileNotFoundError:
        print(f"File not found: {input_file_path}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
