import os
import logging
import asyncio
import replicate
from functools import partial

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
client = replicate.Client(api_token=REPLICATE_API_TOKEN)

async def enhance_image(image_url: str, scale: int = 2):
    """
    Улучшает изображение через GFPGAN (синхронный вызов в потоке).
    """
    try:
        # Синхронный вызов блокирует поток, поэтому запускаем в отдельном потоке
        run_sync = partial(
            replicate.run,
            "tencentarc/gfpgan:9283608cc6b7be6b65a8e44983db012355fde4132009bf99d976b2f0896856a3",
            input={"img": image_url, "scale": scale, "version": "v1.4"}
        )
        output = await asyncio.to_thread(run_sync)
        # output может быть строкой URL или списком
        if isinstance(output, str):
            return output
        elif isinstance(output, list) and output:
            return output[0]
        else:
            logging.error(f"Unexpected output: {output}")
            return None
    except Exception as e:
        logging.error(f"Replicate error: {e}")
        return None