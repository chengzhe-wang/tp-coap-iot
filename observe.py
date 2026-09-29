"""Observation de /temp.
Usage : python observe.py [durée_en_secondes]"""
import asyncio, sys
import aiocoap

async def main(duree):
    ctx = await aiocoap.Context.create_client_context()
    req = aiocoap.Message(code=aiocoap.Code.GET,
                          uri="coap://127.0.0.1/temp", observe=0)
    requete = ctx.request(req)
    premiere = await requete.response
    print(f"réponse initiale : {premiere.payload.decode()}  (Observe={premiere.opt.observe})")

    async def ecouter():
        n = 0
        async for notif in requete.observation:
            n += 1
            print(f"notification {n} : {notif.payload.decode()}  (Observe={notif.opt.observe})")

    try:
        await asyncio.wait_for(ecouter(), duree)
    except asyncio.TimeoutError:
        pass
    requete.observation.cancel()
    print("fin de l'observation")
    await ctx.shutdown()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main(float(sys.argv[1]) if len(sys.argv) > 1 else 10))
