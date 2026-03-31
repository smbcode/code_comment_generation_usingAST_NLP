import os
import json
from datasets import load_dataset
from unsloth import FastLanguageModel
from unsloth import is_bfloat16_supported
from trl import SFTTrainer
from transformers import TrainingArguments

# Configuration
DATASET_PATH = "neurosymbolic_training_dataset.jsonl"
MODEL_NAME = "unsloth/llama-3-8b-Instruct-bnb-4bit" # 4-bit Quantized Llama 3!
MAX_SEQ_LENGTH = 2048

# We use the standard Alpaca prompt template to map your AST (Input) to Comments (Output)
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Input (AST Features JSON):
{input}

### Response (Secure Documented C++ Code):
{output}"""

EOS_TOKEN = "<|eot_id|>" # Llama 3 End of Turn Token

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    for instruction, input, output in zip(instructions, inputs, outputs):
        text = alpaca_prompt.format(instruction=instruction, input=input, output=output) + EOS_TOKEN
        texts.append(text)
    return { "text" : texts, }

def main():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Could not find {DATASET_PATH}. Did you upload it?")

    print("[1] Loading 4-bit Quantized Llama-3...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_NAME,
        max_seq_length = MAX_SEQ_LENGTH,
        dtype = None,            # Automatically detects float16/bfloat16
        load_in_4bit = True,     # Absolute requirement for free Colab T4
    )

    print("[2] Attaching LoRA Adapters for Neurosymbolic Fine-Tuning...")
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16, # Rank of the LoRA matrices (Higher = smarter but slower)
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha = 16,
        lora_dropout = 0, # Dropout = 0 is recommended for Unsloth
        bias = "none",
        use_gradient_checkpointing = "unsloth",
    )

    print("[3] Loading Your Custom AST Dataset...")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    
    # Apply prompt template to all rows
    dataset = dataset.map(formatting_prompts_func, batched = True)

    print(f"Loaded {len(dataset)} training examples!")

    trainer_args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60, # Increase this to 500-1000 for a real training run!
        learning_rate = 2e-4,
        fp16 = not is_bfloat16_supported(),
        bf16 = is_bfloat16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    )

    print("[4] Initializing SFT Trainer...")
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = dataset,
        dataset_text_field = "text",
        max_seq_length = MAX_SEQ_LENGTH,
        dataset_num_proc = 2,
        packing = False, # Can make training 5x faster for short sequences
        args = trainer_args,
    )

    print("[5] Commencing Fine-Tuning... (This will take time)")
    trainer_stats = trainer.train()
    
    print("\n[✔] Training Complete!")

    # Save the Fine-Tuned Model locally
    SAVE_PATH = "neurosymbolic-llama3-lora"
    print(f"[6] Saving Model to: {SAVE_PATH}...")
    model.save_pretrained(SAVE_PATH)
    tokenizer.save_pretrained(SAVE_PATH)
    
    # BONUS: Exporting to GGUF format so you can run it on your RTX 2050 using Ollama!
    print("[7] Exporting to GGUF Format for Local PC usage (RTX 2050)...")
    try:
        model.save_pretrained_gguf("neurosymbolic_model", tokenizer, quantization_method = "q4_k_m")
        print("\n\n🎉 SUCCESS! Download the 'neurosymbolic_model-unsloth.gguf' using the Colab file browser and load it in Ollama/LMStudio locally!")
    except Exception as e:
        print("Note: GGUF export failed, but LoRA adapters were saved successfully.", e)

if __name__ == "__main__":
    main()
