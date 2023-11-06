import json
import multiprocessing
import os
import sys
import grpc
import distributed_banking_system_pb2
import distributed_banking_system_pb2_grpc

OUTPUT_FILE_PATH = "./Output/output.json"


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
    def __init__(self, id, customer_requests):
        # unique ID of the Customer
        self.id = id
        # events from the input
        self.customer_requests = customer_requests
        # a list of received messages used for debugging purpose
        self.recvMsg = list()
        # pointer for the stub
        self.stub = self.createStub()
        # logical clock
        self.logical_clock = 0

    def createStub(self):
        port = str(50050 + int(id))

        address = f"localhost:{port}"
        channel = grpc.insecure_channel(address)
        return distributed_banking_system_pb2_grpc.BankingServiceStub(channel)

    def executeEvents(self):
        banking_service_stub = self.stub
        customer_requests = self.customer_requests
        id = self.id
        event_response = []
        event_sent_ack = []
        for customer_request in customer_requests:
            customer_event, response = self.executeEvent(banking_service_stub, customer_request, id)
            event_response.append(response)
            event_sent_ack.append(customer_event)

        return event_response, event_sent_ack

    def increment_logical_clock(self):
        self.logical_clock += 1

    def executeEvent(self, banking_service_stub, customer_request, id):
        self.increment_logical_clock()
        customer_event = self.append_customer_event_to_recvMsg(customer_request, id)
        customer_request["logical_clock"] = self.logical_clock
        response = banking_service_stub.MsgDelivery(
            distributed_banking_system_pb2.BankingOperationRequest(id=id, type="customer",
                                                                   customer_requests=[customer_request]))
        return customer_event, response

    def update_recvMsg(self, branch_response):
        branch_dict_response = protobuf_to_dict(branch_response)
        self.recvMsg.append(branch_dict_response)
        print(branch_dict_response)

    def append_customer_event_to_recvMsg(self, customer_request, customer_id):
        customer_event = {"id": customer_id,
                          "customer_request_id": customer_request["customer_request_id"],
                          "type": "customer",
                          "logical_clock": self.logical_clock,
                          "interface": customer_request["interface"],
                          "comment": f"event_sent from customer {customer_id}"}
        self.recvMsg.append(customer_event)
        return customer_event


def transform_branch_response_to_json(customer_response):
    result = []
    for response in customer_response:
        result.append(protobuf_to_dict(response)["event_result"])
    return result


def start_customer_process(id, events, result_queue):
    customer = Customer(id, events)
    branch_response, customer_response = customer.executeEvents()
    json_response = transform_branch_response_to_json(branch_response)
    merge_customer_and_branch_response(customer_response, json_response)
    result_queue.put(json_response)


def merge_customer_and_branch_response(customer_response, json_response):
    for i in range(len(json_response)):
        json_response[i].insert(0, customer_response[i])


def get_filtered_results(event_type, results):
    filtered_results = []
    for customer_events in results:
        for customer_event in customer_events:
            for event in customer_event:
                if event['type'] == event_type:
                    filtered_results.append(event)
    return filtered_results


def get_customer_id_events_aggregated_map(filtered_results):
    aggregated_data = {}

    for item in filtered_results:
        id = item['id']
        if id not in aggregated_data:
            aggregated_data[id] = []
        aggregated_data[id].append(item)
    return aggregated_data


def get_sorted_customer_branch_format(aggregated_data, sort_key):
    output = []
    for id, events in aggregated_data.items():
        events = sorted(events, key=lambda d: d[sort_key])
        output.append({"id": id,
                       "type": events[0]["type"],
                       "events": [{"customer-request-id": item["customer_request_id"],
                                   "logical_clock": item["logical_clock"],
                                   "interface": item["interface"],
                                   "comment": item["comment"]}
                                  for item in events]
                       })
    return output


def generate_customer_output(results):
    filtered_results = get_filtered_results("customer", results)
    aggregated_data = get_customer_id_events_aggregated_map(filtered_results)
    customer_output = get_sorted_customer_branch_format(aggregated_data, 'customer_request_id')

    return customer_output


def generate_branch_output(results):
    filtered_results = get_filtered_results("branch", results)
    aggregated_data = get_customer_id_events_aggregated_map(filtered_results)
    branch_output = get_sorted_customer_branch_format(aggregated_data, 'logical_clock')

    return branch_output


def generate_event_output(results):
    flattened_results = []
    for customer_events in results:
        for customer_event in customer_events:
            for event in customer_event:
                flattened_results.append(event)
    events = sorted(flattened_results, key=lambda d: (d['customer_request_id'], d['logical_clock']))
    event_key_transformed_data = [{k.replace('_', '-') if k == 'customer_request_id' else k: v for k, v in item.items()}
                                  for item
                                  in events]
    return event_key_transformed_data


def generate_output(results):
    directory = os.path.dirname(OUTPUT_FILE_PATH)
    if not os.path.exists(directory):
        os.makedirs(directory)
    output_file = open(OUTPUT_FILE_PATH, "a", encoding='utf-8')
    output_file.write(f"// Part 1: List all the events taken place on each customer\n")
    customer_output = generate_customer_output(results)
    output_file.write(json.dumps(customer_output, ensure_ascii=False, indent=4))
    # Testing
    open("./Output/output1.json", "w", encoding='utf-8').write(
        json.dumps(customer_output, ensure_ascii=False, indent=4))

    output_file.write(f"\n// Part 2: List all the events taken place on each branch\n")
    branch_output = generate_branch_output(results)
    output_file.write(json.dumps(branch_output, ensure_ascii=False, indent=4))
    # Testing
    open("./Output/output2.json", "w", encoding='utf-8').write(json.dumps(branch_output, ensure_ascii=False, indent=4))

    output_file.write(
        f"\n// Part 3: List all the events (along with their logical times) triggered by each customer Deposit/Withdraw request\n")
    event_output = generate_event_output(results)
    output_file.write(json.dumps(event_output, ensure_ascii=False, indent=4))
    # Testing
    open("./Output/output3.json", "w", encoding='utf-8').write(json.dumps(event_output, ensure_ascii=False, indent=4))

    output_file.close()


def run_checker_scripts():
    import subprocess

    # Replace 'your-shell-command' with the actual shell command you want to run
    shell_commands = ['python3 ./Checker/checker_part_1.py ./Output/output1.json',
                      'python3 ./Checker/checker_part_2.py ./Output/output2.json',
                      'python3 ./Checker/checker_part_3.py ./Output/output3.json']
    for shell_command in shell_commands:
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
        customers = []
        for item in parsed_data:
            if item["type"] != "customer":
                continue

            id = item["id"]
            type = item["type"]
            customer_requests = item["customer-requests"]
            process = multiprocessing.Process(target=start_customer_process,
                                              args=(id, customer_requests, result_queue))
            processes.append(process)
            process.start()

            # sleep for 3 seconds for event propagation
            # time.sleep(3)

        for process in processes:
            process.join()

        # Retrieve results from the queue
        results = []
        while not result_queue.empty():
            result = result_queue.get()
            results.append(result)
        generate_output(results)
        print("Customer process completed\n")
        run_checker_scripts()
    except FileNotFoundError:
        print(f"File not found: {input_file_path}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
