import json
import uuid

from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer

from datasets import Dataset, load_from_disk
from src.config import PHISH_HTML_EN, PHISH_HTML_EN_QA, PHISH_HTML_EN_QA_LONG_JSONL


def tokenize(batch):
    return tokenizer(
        batch["html"], padding="max_length", truncation=True, return_tensors="pt"
    )


def get_brand_token(batch):
    identified_tokens = []
    start_positions = []
    similarities = []
    for j, input_ids in enumerate(batch["input_ids"]):
        passage = []
        for i in range(len(input_ids) - 2):
            decoded_tokens = tokenizer.decode(
                input_ids[i : i + 3], skip_special_tokens=True
            )
            passage.append(decoded_tokens)
        passage_embedding = st_model.encode(passage)
        query_embedding = st_model.encode(batch["brand"])
        brand_tokens = passage[
            util.dot_score(query_embedding, passage_embedding).argmax()
        ]
        identified_tokens.append([brand_tokens])
        start_position = batch["html"][j].find(brand_tokens)
        if start_position == -1:
            start_position = 0
        start_positions.append([start_position])
        similarity = util.dot_score(query_embedding, passage_embedding).max()
        similarities.append(similarity)
    return {
        "brand_tokens": identified_tokens,
        "start_position": start_positions,
        "similarity": similarities,
    }


def delete_low_similarity_samples(data: Dataset) -> Dataset:
    new_data = []
    for d in data:
        if d["similarity"] > 0.7:
            new_data.append(d)
    return Dataset.from_list(new_data)


def save_sample_dataset_jsonl(data: Dataset):
    cnt = 0
    with open(
        PHISH_HTML_EN_QA_LONG_JSONL,
        "w",
        encoding="utf-8",
        errors="ignore",
    ) as f:
        for d in data:
            chunk = {
                "context": d["html"],
                "answer_text": d["brand_tokens"],
                "start_position": d["start_position"],
                "question": "What is the name of the website's brand?",
            }
            json.dump(chunk, f)
            f.write("\n")
            cnt += 1
            if cnt == 10000:
                break


def create_squad_like_dataset(data: Dataset) -> Dataset:
    new_data = []
    for d in data:
        chunk = {
            "id": str(uuid.uuid4()),
            "context": d["html"],
            "answers": {"answer_start": d["start_position"], "text": d["brand_tokens"]},
            "question": "What is the name of the website's brand?",
            "title": d["brand"],
        }
        new_data.append(chunk)
    return Dataset.from_list(new_data)


if __name__ == "__main__":
    # load dataset
    dataset = load_from_disk(PHISH_HTML_EN)
    # generate target brand list
    phish = Dataset.from_list(dataset["phish"]).shuffle()
    brand_list = list(set(phish["brand"]))

    # load tokenizer
    tokenizer = AutoTokenizer.from_pretrained("deepset/roberta-base-squad2")
    # load sentence transformer model
    st_model = SentenceTransformer("all-MiniLM-L6-v2")

    # tokenize html
    dataset = phish.map(tokenize, batched=True, batch_size=16)
    # identify brand token
    dataset = dataset.map(get_brand_token, batched=True, batch_size=1)
    dataset = delete_low_similarity_samples(dataset)
    print(f"dataset size : {len(dataset)}")
    print(dataset.column_names)
    dataset.remove_columns(["host", "url", "label"])
    save_sample_dataset_jsonl(dataset)
    dataset = create_squad_like_dataset(dataset)

    dataset.save_to_disk(PHISH_HTML_EN_QA)

    for i in range(10):
        print(f"#### sample{i} : {dataset[i]['title']}")
