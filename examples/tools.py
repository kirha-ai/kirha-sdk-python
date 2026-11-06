from kirha import Kirha

kirha = Kirha()

tools = kirha.tools(focus="crypto")
print([tool.name for tool in tools])

page = kirha.tools_page(focus="crypto", page=1, limit=20)
print(page.total, page.limit, page.skip)

matched = kirha.match("what is the price of a coin", focus="crypto", limit=5)
print([(tool.name, tool.related, tool.related_to) for tool in matched])

tool = kirha.get("coingecko_searchCoin")
print(tool.provider, tool.credits_per_call, tool.related_tools)

result = kirha.execute_tool("coingecko_searchCoin", {"query": "avax", "limit": 1})
print(result.output)
