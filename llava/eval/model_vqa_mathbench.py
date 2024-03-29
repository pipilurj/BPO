import argparse
import torch
import os
import json
from tqdm import tqdm
import shortuuid

from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN
from llava.conversation import conv_templates, SeparatorStyle
from llava.model.builder import load_pretrained_model
from llava.utils import disable_torch_init
from llava.mm_utils import tokenizer_image_token, get_model_name_from_path, KeywordsStoppingCriteria

from PIL import Image
import math


def split_list(lst, n):
    """Split a list into n (roughly) equal-sized chunks"""
    chunk_size = math.ceil(len(lst) / n)  # integer division
    return [lst[i:i+chunk_size] for i in range(0, len(lst), chunk_size)]


def get_chunk(lst, n, k):
    chunks = split_list(lst, n)
    return chunks[k]


def eval_model(args):
    # Model
    disable_torch_init()
    model_path = os.path.expanduser(args.model_path)
    model_name = get_model_name_from_path(model_path)
    tokenizer, model, image_processor, context_len = load_pretrained_model(model_path, args.model_base, model_name)
    with open(args.question_file, "r") as f:
        questions = json.load(f)
    questions_all = []
    for key, question_list in questions.items():
        questions_all.extend(question_list)
    questions = questions_all
    # questions = [json.loads(q) for q in open(os.path.expanduser(args.question_file), "r")][0:args.test_size]v
    # questions = [json.loads(q) for q in open(os.path.expanduser(args.question_file), "r")][0:args.test_size]
    questions = get_chunk(questions, args.num_chunks, args.chunk_idx)
    answers_file = os.path.expanduser(args.answers_file)
    os.makedirs(os.path.dirname(answers_file), exist_ok=True)
    ans_file = open(answers_file, "w")
    for line in tqdm(questions):
        image_file = line["ImagePath"]
        gt_answer = line["Answer (final answer highlighted)"]
        genre = image_file.split("/")[0]
        qs = line["Question"]
        cur_prompt = qs
        if args.question_type == "mc":
            qs = "The following is a multi-choice quesiton with an image, please solve it concisely and end with 'The answer is [A/B/C/D/E]'. Do not say you didn't see the image. \n Question: " + qs + "\nAnswer: Let's think step by step."
        elif args.question_type == "free":
            qs = "The following is a free-response quesiton with an image, every question has an deterministic final answer like a value or a word, which will be provided in the problem description. Please solve it concisely and end with 'The answer is \\answer{THE_FIANL_ANSWER}'. \n Question: " + qs + "\nAnswer: Let's think step by step. "
        else:
            raise NotImplementedError(f"{args.question_type} Not implemennted")
        if model.config.mm_use_im_start_end:
            qs = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN + '\n' + qs
        else:
            qs = DEFAULT_IMAGE_TOKEN + '\n' + qs

        conv = conv_templates[args.conv_mode].copy()
        conv.append_message(conv.roles[0], qs)
        conv.append_message(conv.roles[1], None)
        prompt = conv.get_prompt()

        input_ids = tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).cuda()

        if os.path.exists(f"{os.path.join(args.image_folder, image_file)}.png"):
            image = Image.open(f"{os.path.join(args.image_folder, image_file)}.png")
        elif os.path.exists(f"{os.path.join(args.image_folder, image_file)}.jpg"):
            image = Image.open(f"{os.path.join(args.image_folder, image_file)}.jpg")
        else:
            print(f"{os.path.join(args.image_folder, image_file)}.jpg")
            print(f"{os.path.join(args.image_folder, image_file)}.png")
            raise FileNotFoundError(f"Not found for {image_file}")

        image_tensor = image_processor.preprocess(image, return_tensors='pt')['pixel_values'][0]

        stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
        keywords = [stop_str]
        stopping_criteria = KeywordsStoppingCriteria(keywords, tokenizer, input_ids)

        with torch.inference_mode():
            output_ids = model.generate(
                input_ids,
                images=image_tensor.unsqueeze(0).half().cuda(),
                do_sample=True if args.temperature > 0 else False,
                temperature=args.temperature,
                top_p=args.top_p,
                num_beams=args.num_beams,
                # no_repeat_ngram_size=3,
                max_new_tokens=1024,
                use_cache=True)

        input_token_len = input_ids.shape[1]
        n_diff_input_output = (input_ids != output_ids[:, :input_token_len]).sum().item()
        if n_diff_input_output > 0:
            print(f'[Warning] {n_diff_input_output} output_ids are not the same as the input_ids')
        outputs = tokenizer.batch_decode(output_ids[:, input_token_len:], skip_special_tokens=True)[0]
        outputs = outputs.strip()
        if outputs.endswith(stop_str):
            outputs = outputs[:-len(stop_str)]
        outputs = outputs.strip()

        ans_id = shortuuid.uuid()
        ans_file.write(json.dumps({"ImagePath": image_file,
                                   "Question": cur_prompt,
                                   "Genre": genre,
                                   "Output": outputs,
                                   "model_id": model_name,
                                   "gt_answer": gt_answer,
                                   "metadata": {}}) + "\n")
        ans_file.flush()
    ans_file.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default="facebook/opt-350m")
    parser.add_argument("--model-base", type=str, default=None)
    parser.add_argument("--image-folder", type=str, default="")
    parser.add_argument("--question-file", type=str, default="tables/question.jsonl")
    parser.add_argument("--answers-file", type=str, default="answer.jsonl")
    parser.add_argument("--conv-mode", type=str, default="llava_v1")
    parser.add_argument("--question_type", type=str, default="mc")
    parser.add_argument("--num-chunks", type=int, default=1)
    parser.add_argument("--chunk-idx", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top_p", type=float, default=None)
    parser.add_argument("--num_beams", type=int, default=1)
    parser.add_argument("--test_size", type=int, default=10000000)
    args = parser.parse_args()

    eval_model(args)
