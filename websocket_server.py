"""
WebSocket 서버 구현 - 다중 유저 채팅 서버
FastAPI + websockets 기반 구현
"""

import asyncio
import json
import logging
from typing import Dict, Set
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WebSocket Chat Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """WebSocket 연결 관리 클래스"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, Dict] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """클라이언트 연결 수락"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0
        }
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, client_id: str):
        """클라이언트 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_info[client_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
            
    async def send_personal_message(self, message: str, client_id: str):
        """특정 클라이언트에게 메시지 전송"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
                self.connection_info[client_id]["last_activity"] = datetime.now().isoformat()
                self.connection_info[client_id]["message_count"] += 1
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast(self, message: str, exclude_client_id: str = None):
        """모든 클라이언트에게 메시지 브로드캐스트"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            if client_id == exclude_client_id:
                continue
                
            try:
                await websocket.send_text(message)
                self.connection_info[client_id]["last_activity"] = datetime.now().isoformat()
                self.connection_info[client_id]["message_count"] += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected_clients.append(client_id)
                
        # 연결이 끊긴 클라이언트 정리
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
    def get_connection_stats(self) -> Dict:
        """연결 통계 반환"""
        return {
            "total_connections": len(self.active_connections),
            "connection_info": self.connection_info
        }

# 글로벌 연결 관리자 인스턴스
manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 엔드포인트"""
    await manager.connect(websocket, client_id)
    
    try:
        # 연결 성공 메시지 전송
        welcome_message = json.dumps({
            "type": "system",
            "message": f"Welcome {client_id}!",
            "timestamp": datetime.now().isoformat(),
            "total_connections": len(manager.active_connections)
        })
        await manager.send_personal_message(welcome_message, client_id)
        
        # 연결 알림 브로드캐스트
        connection_message = json.dumps({
            "type": "system",
            "message": f"User {client_id} joined the chat",
            "timestamp": datetime.now().isoformat(),
            "total_connections": len(manager.active_connections)
        })
        await manager.broadcast(connection_message, exclude_client_id=client_id)
        
        # 메시지 수신 루프
        while True:
            data = await websocket.receive_text()
            
            # 메시지 처리
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "chat")
                message_content = message_data.get("message", "")
                
                # 채팅 메시지 브로드캐스트
                if message_type == "chat":
                    broadcast_message = json.dumps({
                        "type": "chat",
                        "sender": client_id,
                        "message": message_content,
                        "timestamp": datetime.now().isoformat()
                    })
                    await manager.broadcast(broadcast_message, exclude_client_id=client_id)
                    
                # 시스템 메시지
                elif message_type == "system":
                    logger.info(f"System message from {client_id}: {message_content}")
                    
            except json.JSONDecodeError:
                # 텍스트 메시지 처리
                broadcast_message = json.dumps({
                    "type": "chat",
                    "sender": client_id,
                    "message": data,
                    "timestamp": datetime.now().isoformat()
                })
                await manager.broadcast(broadcast_message, exclude_client_id=client_id)
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.error(f"Error in websocket endpoint for {client_id}: {e}")
    finally:
        manager.disconnect(client_id)
        
        # 연결 해제 알림 브로드캐스트
        disconnect_message = json.dumps({
            "type": "system",
            "message": f"User {client_id} left the chat",
            "timestamp": datetime.now().isoformat(),
            "total_connections": len(manager.active_connections)
        })
        await manager.broadcast(disconnect_message)

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "connections": len(manager.active_connections)
    }

@app.get("/stats")
async def get_stats():
    """연결 통계 엔드포인트"""
    return manager.get_connection_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)