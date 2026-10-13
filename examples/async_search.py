import asyncio

from kirha import AsyncKirha


async def main() -> None:
    async with AsyncKirha(focus="crypto") as kirha:
        bitcoin, ethereum = await asyncio.gather(
            kirha.search("What is the current Bitcoin price in USD?"),
            kirha.search("What is the current Ethereum price in USD?"),
        )

    print(bitcoin.data)
    print(ethereum.data)


asyncio.run(main())
