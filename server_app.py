import socketio
from IKSAN.src.tod import TodInputModule
import uvicorn
import pandas as pd

sio = socketio.AsyncServer(async_mode='asgi', ping_timeout = 10000, cors_allowed_origins = '*')
app = socketio.ASGIApp(sio)


@sio.on('address')
async def print_message(sid, si_name):
    print("Socket ID: ", sid)
    print(si_name)
    tlLogic_name = [f"{si_name}"]
    k_0 = [0, 0, 0, 0]
    k_1 = [0, 0, 0, 0]
    k_2 = [0, 0, 0, 0]
    k_cen = [k_0] + [k_1] + [k_2]
    tod_input_module = TodInputModule(len(tlLogic_name), tlLogic_name, k_0, k_1, k_2, k_cen)
    data = tod_input_module.create_tod_table()
    print(data)
    await sio.emit('tod_table', data)

if __name__ == "__main__":
    
    uvicorn.run(
        "server_app:app",
        
        host="192.168.1.131",
        
        port=8000,
        
        reload=True
    )