import wharf

client = wharf.Client(token="SomeToken", intents=wharf.Intents.all())


@client.listen("ready")
async def ready(data):
    print("Im ready :D")


@client.listen("message_create")
async def message_create(message):
    if message.content == ".hi":
        await client.send(message.channel_id, "hi :)")


client.run()
