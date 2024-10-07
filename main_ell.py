from pathlib import Path
import ell
from pydantic import BaseModel, Field
from rich.console import Console


MODEL = "claude-3-5-sonnet-20240620"


class ScoreAgent:
    class InteractionScore(BaseModel):
        score: int = Field(description="Conversation rating", ge=1, le=100)

    _validator = InteractionScore.model_validate_json  # hack that allows us to use the pydantic model's validation function without this class existing outside of our agent definition

    persona = ell.system(
        f"You're a couples therapist listening in on the conversation outlined in this script. You rate interactions on a scale of 1-100. You must absolutely respond in this format with no exceptions.\n{InteractionScore.model_json_schema()}"
    )

    @ell.complex(model=MODEL, temperature=0.7, max_tokens=100)
    def _score_interaction(
        self, script: str, ai_name: str, player_name: str, goal: str
    ):
        prompt = (
            f"Below is the transcript of a conversation between {ai_name} and {player_name}\n"
            f"{script}\n"
            f"On a scale of 1-100 (1=strongly disagree, 100=strongly agree), how much  would you agree with the following statement: {goal}\n"
        )
        return [self.persona, ell.user(prompt)]

    # TODO: this is pretty ugly, but I wanted to keep the schema within this class so that everything is in one place
    def score_interaction(self, script: str, ai_name: str, player_name: str, goal: str):
        message = self._score_interaction(script, ai_name, player_name, goal)
        return self._validator(message.content[0].text).score


class ScriptAgent:
    class ScriptContinuation(BaseModel):
        next_line: str = Field(description="The next line of the script")

    _validator = ScriptContinuation.model_validate_json

    persona = ell.system(
        f"You're a professional script writer. You're given a description of the character, and a current script. Complete the next line of the script in the most realistic way possible. You must absolutely respond in this format with no exceptions.\n{ScriptContinuation.model_json_schema()}"
    )

    def __init__(self, speaker: str):
        self.speaker = speaker

    @ell.complex(model=MODEL, temperature=0.7, max_tokens=100)
    def _write(self, profile: str, script: str):
        """You're a professional script writer. You're given a description of the character, and a current script. Complete the next line of the script in the most realistic way possible. Include no explanation of your reasoning."""
        prompt = (
            "Here's a description of our character's psyche and personality traits:\n"
            f"{profile}\n"
            "Here's an existing script. Predict the next line of the script but only what {speaker} says\n"
            f"SCRIPT:{script}\n"
            f"{self.speaker}:"
        )
        return [self.persona, ell.user(prompt)]

    def write(self, profile: str, script: str):
        message = self._write(profile, script)
        return self._validator(message.content[0].text).next_line


def quit_on_empty_input(user_input):
    if not user_input:
        raise KeyboardInterrupt()
    return user_input


def update_script(current_script, new_line):
    return current_script + "\n" + new_line + "\n"


#### GET SCENARIO AND PROFILE ####
ALL_SCENARIOS = ["001_maya", "002_jill"]
scenario = quit_on_empty_input(input("Choose a scenario: 001_maya | 002_jill: "))
assert scenario in ALL_SCENARIOS
GAMES_DIR = Path(__file__).parent / "games" / scenario
PROFILE_FILE = GAMES_DIR / "profile.txt"
PRESCRIPT_FILE = GAMES_DIR / "prescript.txt"
with open(PROFILE_FILE, "r") as f:
    profile = f.read()

with open(PRESCRIPT_FILE, "r") as f:
    script = f.read()

#### SET UP AGENTS ####
ai_name = scenario.split("_")[1].upper()
player_name = quit_on_empty_input(input("Enter your name: ").upper())
goal = f"{player_name} successfully solicited affection from {ai_name}"
NUM_TURNS = 10
score_agent = ScoreAgent()
script_agent = ScriptAgent(ai_name)

#### START CONVERSATION ####
console = Console()
for i in range(NUM_TURNS):
    console.print(f"[green]#### Attempt {i+1} out of {NUM_TURNS} ####")
    print("\n")
    console.print("[blue]" + script)
    user_input = quit_on_empty_input(input(f"{player_name}: "))

    #### USER ANSWERS ####
    user_input = f"{player_name}: {user_input}"
    script = update_script(script, user_input)

    #### AI ANSWERS ####
    ai_response = script_agent.write(profile, script)
    ai_response = f"{ai_name}: {ai_response}"
    console.print("\n[red bold]" + ai_response)
    script = update_script(script, ai_response)

    #### JUDGE SCORE ####
    judge_response = score_agent.score_interaction(script, ai_name, player_name, goal)
    console.print("\n[yellow bold]" + f"Judge: {judge_response}")

    print("\n")