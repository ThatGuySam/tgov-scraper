import aiohttp


async def async_get_json(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            json = await response.json()
    return json
