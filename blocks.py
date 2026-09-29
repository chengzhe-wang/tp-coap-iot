"""Télécharge /biglog bloc par bloc (Block2) avec une taille imposée.
Usage : python blocks.py 256   (tailles possibles : 16,32,64,128,256,512,1024)"""
import asyncio, sys, math
import aiocoap
from aiocoap.optiontypes import BlockOption

async def main(taille):
    szx = int(math.log2(taille)) - 4
    ctx = await aiocoap.Context.create_client_context()
    numero, total = 0, b""
    while True:
        req = aiocoap.Message(code=aiocoap.Code.GET, uri="coap://127.0.0.1/biglog")
        req.opt.block2 = BlockOption.BlockwiseTuple(numero, False, szx)
        rep = await ctx.request(req, handle_blockwise=False).response
        b = rep.opt.block2
        print(f"bloc {b.block_number:2d}  taille {len(rep.payload):4d} o  more={b.more}")
        total += rep.payload
        if not b.more:
            break
        numero += 1
    print(f"TOTAL : {len(total)} octets en {numero + 1} blocs de {taille} o")
    await ctx.shutdown()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 256))
