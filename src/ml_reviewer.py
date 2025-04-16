from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import subprocess
import os

model_name = "Salesforce/codet5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# Get list of changed Python files
git_diff_cmd = "git diff --name-only origin/main HEAD"
changed_files = subprocess.check_output(git_diff_cmd.split()).decode().splitlines()

suggestions = []
print("Test Review PR")
for file in changed_files:
    if file.endswith(".py"):
        with open(file, "r") as f:
            code = f.read()
            prompt = "review code: " + code
            inputs = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=512)
            outputs = model.generate(inputs, max_length=256)
            review = tokenizer.decode(outputs[0], skip_special_tokens=True)
            suggestions.append(f"**{file}**:\n{review}\n")

with open("suggestions.txt", "w") as f:
    f.write("\n".join(suggestions))