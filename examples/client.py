import wharf

client = wharf.Client(token="SomeToken", intents=wharf.Intents.all())


@client.listen("ready")
async def ready(data):
    print("Im ready :D")


@client.listen("message_create")
async def message_create(data):
    if data["content"] == ".hi":
        await client.send(data["channel_id"], "hi :)")


client.run()
