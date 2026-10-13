from kirha import Kirha

kirha = Kirha()

result = kirha.search(
    "List top 10 stablecoins yield on Ethereum",
    summarization={"instruction": "Format the response as a table"},
)

print(result.summary)
