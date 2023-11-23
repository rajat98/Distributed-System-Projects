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
        self.stub = self.createStub(events)

    def createStub(self, events):
        stub_dict = {}
        branch_ids = set()
        for event in events:
            branch_ids.add(event["branch"])

        for id in branch_ids:
            port = str(50050 + int(id))

            address = f"localhost:{port}"
            channel = grpc.insecure_channel(address)
            stub_dict[id] = distributed_banking_system_pb2_grpc.BankingServiceStub(channel)

        return stub_dict

    def executeEvents(self):
        banking_service_stub_dict = self.stub
        events = self.events
        id = self.id
        responses = []
        for event in events:
            branch_id = event["branch"]
            event.pop('branch', None)
            response = banking_service_stub_dict[branch_id].MsgDelivery(
                distributed_banking_system_pb2.BankingOperationRequest(id=id, type="customer", events=[event]))
            responses.append(response)
        return responses

    def update_recvMsg(self, branch_response):
        for response in branch_response:
            branch_dict_response = protobuf_to_dict(response)
            self.recvMsg.append(branch_dict_response)

        return self.recvMsg


def start_customer_process(id, events):
    customer = Customer(id, events)
    branch_response = customer.executeEvents()
    branch_response = customer.update_recvMsg(branch_response)

    directory = os.path.dirname(OUTPUT_FILE_PATH)
    if not os.path.exists(directory):
        os.makedirs(directory)

    output_file = open(OUTPUT_FILE_PATH, "w")
    output_file.write(json.dumps(branch_response, indent=4))
    # output_file.write(dict_to_str(branch_response))
    output_file.close()

def run_checker_scripts():
    import subprocess

    # Replace 'your-shell-command' with the actual shell command you want to run
    shell_command = 'python3 ./Checker/checker.py ./Output/output.json'

    # Run the shell command
    result = subprocess.run(shell_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Check if the command was successful
    if result.returncode == 0:
        print("Command executed successfully")
        print("Standard Output:")
        print(result.stdout)
    else:
        print("Error executing the command")
        print("Standard Error:")
        print(result.stderr)


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
            # time.sleep(3)
        for process in processes:
            process.join()
        run_checker_scripts()
        print("Customer process completed\n")
    except FileNotFoundError:
        print(f"File not found: {input_file_path}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
