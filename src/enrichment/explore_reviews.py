from datasets import load_dataset

dataset = load_dataset("SetFit/amazon_reviews_multi_fr", split="train", streaming=True)

print("\nEXEMPLES D'AVIS CLIENTS\n")

for i, review in enumerate(dataset):
    print("=" * 60)
    print("Avis :", i + 1)
    print("Note :", int(review["label"]) + 1)
    print("Texte :", str(review["text"])[:500])

    if i >= 9:
        break
