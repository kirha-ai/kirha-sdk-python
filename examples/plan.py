from kirha import Kirha

kirha = Kirha()

plan = kirha.plan(
    "Find engineers working at companies behind the latest patents in Machine Learning"
)

print("Plan ID:", plan.id)
print("Steps:", plan.steps)
print("Estimated usage:", plan.usage.estimated)

result = plan.execute()
print(result.data)
