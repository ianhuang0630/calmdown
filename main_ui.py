import os
import json
import streamlit as st
from datetime import datetime
from tasksolver.common import Question, ParsedAnswer, TaskSpec
from tasksolver.gpt4v import GPTModel
from tasksolver.claude import ClaudeModel
from tasksolver.answer_types import TextAnswer, Number
from tasksolver.utils import docs_for_GPT4
from rich.console import Console

# TODO: multi-sample reply
# TODO: selection according to match to character profile   


def main():
    st.title("Calmdown")

    console = Console()

    # load the character backstories, and script 
    game = "games/002_jill" 

    with open("creds/openai_key.txt", "r") as f: 
        openai_key = f.readline().strip()
    with open("creds/claude_key.txt", "r") as f: 
        claude_key = f.readline().strip()

    with open(os.path.join(game, "profile.txt"), "r") as f:
        profile  = f.read()
    with open(os.path.join(game, "prescript.txt"), "r") as f:
        script = f.read()
    with open(os.path.join(game, "goal.txt"), "r") as f:
        goal = f.read()
    with open(os.path.join(game, "roles.json"), "r") as f:
        roles = json.load(f)



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

    ai =  GPTModel(openai_key,
             task=script_writing,
             model="gpt-4-vision-preview")
    
    judge =  GPTModel(openai_key,
             task=score_interaction,
             model="gpt-4-vision-preview")

    characters = [roles["player"], roles["ai"]] 
    existing_script = []

    for line in script.split("\n"):
        if len(line.strip()) > 0: 
            if any([line.startswith(el+":")  for el in characters]):
                colon = line.find(":")
                character = line[:colon].strip()
                script = line[colon+1:].strip()
            else:
                character = "narrator"
                script =  line
            existing_script.append({"role": character, "content": script})
        

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = existing_script # [{"role": "narrator", "content": "the start of the story", "time": get_current_time()}]
    
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        if message["role"] == "narrator":
            st.markdown(f"<div><i>{message['content']}<i></div>", unsafe_allow_html=True)
        if message["role"] != "narrator":
            with st.chat_message(message["role"]):
                st.markdown(f"{message['content']}")

    # React to user input
    if prompt := st.chat_input(f"You're {characters[0]}. What do you say?"):
        # Display user message in chat message container
        with st.chat_message(characters[0]):
            st.markdown(f"{prompt}")
        # Add user message to chat history
        st.session_state.messages.append({"role": characters[0], "content": prompt})
        existing_script.append({"role":  characters[0], "content": prompt})    

        # compose script,
        script_str = ""
        for line in existing_script:
            if line["role"] != "narrator":
                script_str += "\n" + f'{line["role"]}: {line["content"]}'+"\n\n"
            else:
                script_str += line["content"]+"\n"

        
        prompt =  Question([
            "Here's a description of our character's psyche and personality traits:",
            profile,
            f"Here's an existing script. Predict the next line, but only what {characters[1]} says. Start with '{characters[1]}:', or a narrative line. ENSURE THAT THE SCRIPT CAPTURES THEIR PSYCHE.",
            "SCRIPT:",
            script_str
        ])
        p_ans, _ , _, _ = ai.run_once(prompt)


        # let's respond with 
        for line in p_ans.data.split("\n"):
            if len(line.strip()) > 0: 
                if any([line.startswith(el+":")  for el in characters]):
                    colon = line.find(":")
                    character = line[:colon].strip()
                    script = line[colon+1:].strip()
                else:
                    character = "narrator"
                    script =  line
                existing_script.append({"role": character, "content": script})

                if character == "narrator":
                    st.markdown(f"<div><i>{script}<i></div>", unsafe_allow_html=True)
            
                if character != "narrator":
                    with st.chat_message(character):
                        st.markdown(f"{script}")

                # Add assistant response to chat history
                st.session_state.messages.append({"role": character, "content": script})

        # eval          
        script_str = ""
        for line in existing_script:
            if line["role"] != "narrator":
                script_str += "\n" + f'{line["role"]}: {line["content"]}'+"\n\n"
            else:
                script_str += line["content"]+"\n"

        judge_prompt = Question([
            f"Below is the transcript of a conversation between {characters[0]} and {characters[1]}",
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


        

if __name__ == "__main__":
    main()
