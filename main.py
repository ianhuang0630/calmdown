from tasksolver.common import Question, ParsedAnswer, TaskSpec
from tasksolver.gpt4v import GPTModel
from tasksolver.answer_types import TextAnswer, Number
from tasksolver.utils import docs_for_GPT4
from rich.console import Console


if __name__ == "__main__":  

    console = Console()
    with open("openai_key.txt", "r") as f: 
        openai_key = f.readline().strip()

    script_writing = TaskSpec(
        name="Complete the next line of the script",
        description="You're a professional script writer. You're given a description of the character, and a current script. Complete the next line of the script in the most realistic way possible.",
        answer_type=TextAnswer,
        followup_func=None,
        completed_func=None
    )


    score_interaction = TaskSpec(
        name="Evaluate the following interaction between the characters in this script",
        description="You're a couples therapist listening in on the conversation outlined in this script. You rate interactions on a scale of 1-100.",
        answer_type=Number,
        followup_func = None,
        completed_func=None
    )
    score_interaction.add_background(
        Question([
            "Read the following for the docs of the parser, which will parse your response, to guide the format of your responses:" , 
            docs_for_GPT4(Number.parser) 
        ])
    )

    
    ai = GPTModel(openai_key,
             task=script_writing,
             model="gpt-4-vision-preview")

    judge =  GPTModel(openai_key,
             task=score_interaction,
             model="gpt-4-vision-preview")
    
    with  open("jill_profile.txt", "r") as f:
        profile  = f.read()

    with open("jill_prescript.txt", "r") as f:
        script = f.read()
        
    ai_name = "JILL"
    player_name = "ALEX"
    goal = f"{player_name} successfully solicited affection from {ai_name}"
    num_tries  = 10

    for i in range(num_tries):
        console.print(f"[green]#######################{i}######################")
        console.print("[blue]" + script)
        user_input = input(f"{player_name}: ")    
        
        user_input = f"{player_name}\n{user_input}"
        script += "\n" + user_input
    
        prompt =  Question([
            "Here's a description of our character's psyche and personality traits:",
            profile,
            f"Here's an existing script. Predict the next line, but only what {ai_name} says."
            "SCRIPT:",
            script
        ])
        
        p_ans, _ , _, _ = ai.run_once(prompt)

        console.print("[red bold]" + p_ans.data) 
        script += "\n\n" + p_ans.data



        ############## judge code
        judge_prompt = Question([
            f"Below is the transcript of a conversation between {ai_name} and {player_name}",
            script,
            f"On a scale of 1-100 (1=strongly disagree, 100=strongly agree), how much  would you agree with the following statement: {goal}" 
        ]) 
        
        works = False
        max_tries = 10
        trie = 0 
        while not works and trie < max_tries:
            try: 
                p_ans, _, _, _ = judge.run_once(judge_prompt) 
                works = True
            except:
                print("error parsing. trying again.")
                trie += 1
        console.print(f"[yellow bold] Judge: {p_ans.data}") 

        
    
    # character -- weaknesses, strengths
    # script
    
    # player is allowed to write one line of script.

    # goal: in a certain number of moves (dialogue), de-escalate
    # Scores the escalation, downward delta  is number points.
    # analyzes blunders in terms of delta escalation.

    