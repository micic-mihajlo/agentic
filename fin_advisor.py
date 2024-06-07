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

ORCHESTRATOR_MODEL = "gemini-1.5-pro"
FINANCIAL_AGENT_MODEL = "gemini-1.5-pro"
REFINER_MODEL = "gemini-1.5-flash"

console = Console()

user_data = {
    'income': 5000,
    'expenses': [
        {'category': 'Rent', 'amount': 1500},
        {'category': 'Groceries', 'amount': 500},
        {'category': 'Utilities', 'amount': 200},
        {'category': 'Transportation', 'amount': 300},
        {'category': 'Entertainment', 'amount': 400},
        {'category': 'Misc', 'amount': 200}
    ],
    'bank_accounts': [
        {'name': 'Checking', 'balance': 2000},
        {'name': 'Savings', 'balance': 5000}
    ],
    'credit_cards': [
        {'name': 'Card 1', 'balance': 1000, 'interest_rate': 0.15},
        {'name': 'Card 2', 'balance': 500, 'interest_rate': 0.12}
    ],
    'investments': [
        {'name': 'Stock 1', 'value': 2000},
        {'name': 'Stock 2', 'value': 3000},
        {'name': 'Bond 1', 'value': 1000}
    ],
    'financial_goals': [
        {'name': 'House Down Payment', 'target': 10000, 'deadline': '2025-06-30'},
        {'name': 'Retirement', 'target': 500000, 'deadline': '2045-12-31'}
    ]
}

def orchestrator(objective, user_data, completion_check_prompt=None):
    console.print(f"\n[bold]Calling Orchestrator for your objective[/bold]")

    model = genai.GenerativeModel(ORCHESTRATOR_MODEL)
    
    prompt = f"Based on the following objective and the provided user financial data, please break down the objective into sub-tasks and create concise and detailed prompts for the financial agent to execute each task. Assess if the objective has been fully achieved based on the sub-task results.\n\nObjective: {objective}\n\nUser Data: {json.dumps(user_data)}"

    if completion_check_prompt:
        prompt = completion_check_prompt

    response = model.generate_content(prompt, request_options={'retry': retry.Retry()})
    response_text = response.text

    console.print(Panel(response_text, title=f"[bold green]Orchestrator[/bold green]", title_align="left", border_style="green", subtitle="Sending tasks to financial agent 👇"))

    return response_text

def financial_agent(prompt, user_data):
    system_message = (
        "You are an expert financial agent. Your goal is to execute financial analysis tasks accurately and provide detailed explanations of your reasoning."
    )

    model = genai.GenerativeModel(FINANCIAL_AGENT_MODEL)

    full_prompt = f"{system_message}\n{prompt}\nUser Data: {json.dumps(user_data)}"

    response = model.generate_content(full_prompt, request_options={'retry': retry.Retry()})
    response_text = response.text

    console.print(Panel(response_text, title="[bold blue]Financial Agent Result[/bold blue]", title_align="left", border_style="blue", subtitle="Task completed, sending result to Orchestrator 👇"))

    return response_text

def refiner(objective, sub_task_results, user_data):
    console.print("\nCalling Refiner to provide the optimized financial plan:")

    model = genai.GenerativeModel(REFINER_MODEL)

    prompt = f"Objective: {objective}\n\nSub-task results:\n{sub_task_results}\n\nPlease review and refine the sub-task results into a cohesive optimized financial plan. Ensure the plan is consistent with the current user financial data. Suggest any necessary updates to the user data based on the optimized plan.\n\nUser Data: {json.dumps(user_data)}"

    response = model.generate_content(prompt, request_options={'retry': retry.Retry()})
    response_text = response.text
    console.print(Panel(response_text, title="[bold green]Optimized Financial Plan[/bold green]", title_align="left", border_style="green"))

    return response_text

def main():
    objective = input("Please enter your financial optimization objective: ")

    task_results = []

    while True:
        orchestrator_result = orchestrator(objective, user_data)

        if "Task complete" in orchestrator_result:
            final_output = orchestrator_result
            break
        else:
            sub_task_prompt = orchestrator_result
            sub_task_result = financial_agent(sub_task_prompt, user_data)
            task_results.append(sub_task_result)

            completion_check_prompt = (
                f"Based on the current sub-task results:\n\n{sub_task_result}\n\n"
                f"Please assess if the financial optimization task is complete. "
                f"If it is, simply respond with 'Task complete'. "
                f"If not, provide the next sub-task prompt."
            )
            completion_check_result = orchestrator(objective, user_data, completion_check_prompt)

            if "Task complete" in completion_check_result:
                final_output = "\n".join(task_results)
                break

    refined_output = refiner(objective, final_output, user_data)

    console.print(f"\n[bold]Optimized Financial Plan:[/bold]\n{refined_output}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"financial_optimization_{timestamp}.txt"

    with open(filename, 'w') as file:
        file.write(f"Objective: {objective}\n\n")
        file.write("=" * 40 + " Task Breakdown " + "=" * 40 + "\n\n")
        file.write(final_output + "\n\n")
        file.write("=" * 40 + " Optimized Financial Plan " + "=" * 40 + "\n\n")
        file.write(refined_output)

    print(f"\nFinancial optimization plan saved to {filename}")

if __name__ == "__main__":
    main()