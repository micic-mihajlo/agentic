import os
import json
from rich.console import Console
from rich.panel import Panel
from datetime import datetime
import google.generativeai as genai
from google.api_core import retry
from dotenv import load_dotenv

load_dotenv()

os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Define the models to be used for each stage
ORCHESTRATOR_MODEL = "gemini-1.5-flash" 
SUPPLY_CHAIN_AGENT_MODEL = "gemini-1.5-flash"
REFINER_MODEL = "gemini-1.5-flash"

# Initialize the Rich Console
console = Console()

# Mock database using objects
products = [
    {'id': 1, 'name': 'T-Shirt', 'inventory': 100, 'price': 19.99},
    {'id': 2, 'name': 'Jeans', 'inventory': 75, 'price': 49.99},
    {'id': 3, 'name': 'Dress', 'inventory': 50, 'price': 79.99},
    {'id': 4, 'name': 'Sneakers', 'inventory': 80, 'price': 59.99},
    {'id': 5, 'name': 'Jacket', 'inventory': 60, 'price': 99.99},
    {'id': 6, 'name': 'Shorts', 'inventory': 90, 'price': 29.99},
    {'id': 7, 'name': 'Sweater', 'inventory': 70, 'price': 39.99}
]

suppliers = [
    {'id': 1, 'name': 'Supplier A', 'lead_time': 5, 'reliability': 0.95},
    {'id': 2, 'name': 'Supplier B', 'lead_time': 3, 'reliability': 0.56},
    {'id': 3, 'name': 'Supplier C', 'lead_time': 7, 'reliability': 0.98},
    {'id': 4, 'name': 'Supplier D', 'lead_time': 4, 'reliability': 0.92},
    {'id': 5, 'name': 'Supplier E', 'lead_time': 6, 'reliability': 0.96},
    {'id': 6, 'name': 'Supplier F', 'lead_time': 5, 'reliability': 0.94},
    {'id': 7, 'name': 'Supplier G', 'lead_time': 4, 'reliability': 0.93}
]

orders = [
    {'id': 1, 'product_id': 1, 'quantity': 50, 'due_date': '2023-06-30'},
    {'id': 2, 'product_id': 2, 'quantity': 30, 'due_date': '2023-07-15'},
    {'id': 3, 'product_id': 3, 'quantity': 20, 'due_date': '2023-08-10'},
    {'id': 4, 'product_id': 4, 'quantity': 40, 'due_date': '2023-09-05'},
    {'id': 5, 'product_id': 5, 'quantity': 25, 'due_date': '2023-10-20'},
    {'id': 6, 'product_id': 6, 'quantity': 35, 'due_date': '2023-11-01'},
    {'id': 7, 'product_id': 7, 'quantity': 45, 'due_date': '2023-12-15'}
]

def orchestrator(objective, products, suppliers, orders, completion_check_prompt=None):
    console.print(f"\n[bold]Calling Orchestrator for your objective[/bold]")

    model = genai.GenerativeModel(ORCHESTRATOR_MODEL)
    
    prompt = f"Based on the following objective and the provided product, supplier, and order data, please break down the objective into 3-4 sub-tasks and create concise and detailed prompts for the supply chain agent to execute each task. Assess if the objective has been fully achieved based on the sub-task results.\n\nObjective: {objective}\n\nProducts: {json.dumps(products)}\n\nSuppliers: {json.dumps(suppliers)}\n\nOrders: {json.dumps(orders)}"

    if completion_check_prompt:
        prompt = completion_check_prompt

    response = model.generate_content(prompt, request_options={'retry': retry.Retry()}) # Added retry for robustness
    response_text = response.text

    console.print(Panel(response_text, title=f"[bold green]Orchestrator[/bold green]", title_align="left", border_style="green", subtitle="Sending tasks to supply chain agent 👇"))

    return response_text

def supply_chain_agent(prompt, products, suppliers, orders):
    system_message = (
        "You are an expert supply chain agent. Your goal is to execute supply chain optimization tasks accurately and provide detailed explanations of your reasoning."
    )

    model = genai.GenerativeModel(SUPPLY_CHAIN_AGENT_MODEL)

    full_prompt = f"{system_message}\n{prompt}\nProducts: {json.dumps(products)}\nSuppliers: {json.dumps(suppliers)}\nOrders: {json.dumps(orders)}"

    response = model.generate_content(full_prompt, request_options={'retry': retry.Retry()})
    response_text = response.text

    console.print(Panel(response_text, title="[bold blue]Supply Chain Agent Result[/bold blue]", title_align="left", border_style="blue", subtitle="Task completed, sending result to Orchestrator 👇"))

    return response_text

def refiner(objective, sub_task_results, products, suppliers, orders):
    console.print("\nCalling Refiner to provide the optimized supply chain plan:")

    model = genai.GenerativeModel(REFINER_MODEL)

    prompt = f"Objective: {objective}\n\nSub-task results:\n{sub_task_results}\n\nPlease review and refine the sub-task results into a cohesive optimized supply chain plan. Ensure the plan is consistent with the current product, supplier, and order data. Suggest any necessary updates to the database based on the optimized plan.\n\nProducts: {json.dumps(products)}\nSuppliers: {json.dumps(suppliers)}\nOrders: {json.dumps(orders)}"

    response = model.generate_content(prompt, request_options={'retry': retry.Retry()})
    response_text = response.text
    console.print(Panel(response_text, title="[bold green]Optimized Supply Chain Plan[/bold green]", title_align="left", border_style="green"))

    return response_text
def main():
    objective = input("Please enter your supply chain optimization objective: ")

    task_results = []

    while True:
        orchestrator_result = orchestrator(objective, products, suppliers, orders)

        if "Task complete" in orchestrator_result:
            final_output = orchestrator_result
            break
        else:
            sub_task_prompt = orchestrator_result
            sub_task_result = supply_chain_agent(sub_task_prompt, products, suppliers, orders)
            task_results.append(sub_task_result)

            # Prompt the orchestrator to check if the task is done
            completion_check_prompt = (
                f"Based on the current sub-task results:\n\n{sub_task_result}\n\n"
                f"Please assess if the supply chain optimization task is complete. "
                f"If it is, simply respond with 'Task complete'. "
                f"If not, provide the next sub-task prompt."
            )
            completion_check_result = orchestrator(objective, products, suppliers, orders, completion_check_prompt)

            if "Task complete" in completion_check_result:
                final_output = "\n".join(task_results)
                break

    refined_output = refiner(objective, final_output, products, suppliers, orders)

    console.print(f"\n[bold]Optimized Supply Chain Plan:[/bold]\n{refined_output}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"supply_chain_optimization_{timestamp}.txt"

    with open(filename, 'w') as file:
        file.write(f"Objective: {objective}\n\n")
        file.write("=" * 40 + " Task Breakdown " + "=" * 40 + "\n\n")
        file.write(final_output + "\n\n")
        file.write("=" * 40 + " Optimized Supply Chain Plan " + "=" * 40 + "\n\n")
        file.write(refined_output)

    print(f"\nSupply chain optimization plan saved to {filename}")

if __name__ == "__main__":
    main()