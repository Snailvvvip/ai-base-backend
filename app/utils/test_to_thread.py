import asyncio
import time


async def main():
  common_counter = 0

  async def async_delay(name: str):
    nonlocal common_counter
    # current_counter = common_counter
    await asyncio.sleep(0.5)
    print(f"{name},111\n")
    print(f"{name},222\n")
    common_counter = common_counter + 1
    print(f"{name},333\n")
    print(f"{name}[common_counter]:{common_counter}\n")
    print(f"{name},444\n")

  start_time = time.time()

  # sync_delay("1")
  # sync_delay("2")
  # sync_delay("3")

  # await asyncio.gather(
  #   asyncio.create_task(asyncio.to_thread(sync_delay, name="A")),
  #   asyncio.create_task(asyncio.to_thread(sync_delay, name="B")),
  #   asyncio.create_task(asyncio.to_thread(sync_delay, name="C")),
  # )

  await asyncio.gather(
    asyncio.create_task(async_delay(name="A")),
    asyncio.create_task(async_delay(name="B")),
    asyncio.create_task(async_delay(name="C")),
  )

  print("common_counter", common_counter)

  print(f"耗时: {time.time() - start_time}s")


asyncio.run(main())
