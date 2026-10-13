from kirha import Kirha

kirha = Kirha()

tools = kirha.tools(focus="crypto")
print([tool.name for tool in tools])

result = kirha.execute_tool("coingecko_searchCoin", {"query": "avax", "limit": 1})
print(result.output)
