"""
WebSocket 서버 구현 - 다중 유저 채팅 서버
FastAPI + websockets 기반 구현
배치 처리 통합 및 Prometheus 메트릭 수집 포함
"""

import asyncio
import json
import logging
import threading
import time
from typing import Dict, Set, List, Optional
from datetime import datetime
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus 메트릭 정의
websocket_connections = Gauge(
    'websocket_connections', 
    '현재 활성 WebSocket 연결 수'
)
websocket_messages_processed = Counter(
    'websocket_messages_processed_total',
    '처리된 WebSocket 메시지 총 수'
)
websocket_errors = Counter(
    'websocket_errors_total',
    'WebSocket 에러 발생 수'
)
batch_processing_time = Histogram(
    'batch_processing_time_seconds',
    '배치 처리 소요 시간',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)
batch_size = Gauge(
    'batch_size',
    '현재 배치 크기'
)
active_batches = Gauge(
    'active_batches',
    '활성 배치 수'
)

# 배치 처리 설정
BATCH_SIZE = 100  # 배치당 최대 메시지 수
BATCH_TIMEOUT = 1.0  # 배치 처리 최대 대기 시간(초)

class BatchProcessor:
    """비동기 배치 처리 클래스"""
    
    def __init__(self):
        self.message_queue = asyncio.Queue()
        self.batch_lock = threading.Lock()
        self.active = True
        self.current_batch: List[Dict] = []
        self.batch_processing_task = None
        
    async def start(self):
        """배치 처리 시작"""
        self.batch_processing_task = asyncio.create_task(self._process_batches())
        logger.info("Batch processor started")
        
    async def stop(self):
        """배치 처리 중지"""
        self.active = False
        if self.batch_processing_task:
            self.batch_processing_task.cancel()
            try:
                await self.batch_processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Batch processor stopped")
        
    async def add_message(self, message: Dict):
        """메시지를 배치 큐에 추가"""
        await self.message_queue.put(message)
        
    async def _process_batches(self):
        """배치 처리 메인 루프"""
        while self.active:
            try:
                # 배치 수집
                batch = await self._collect_batch()
                
                if batch:
                    # 배치 처리
                    await self._process_single_batch(batch)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")
                websocket_errors.inc()
                await asyncio.sleep(0.1)
                
    async def _collect_batch(self) -> List[Dict]:
        """배치 수집"""
        batch = []
        start_time = time.time()
        
        while len(batch) < BATCH_SIZE:
            try:
                # 메시지 큐에서 메시지 가져오기 (타임아웃 설정)
                timeout = BATCH_TIMEOUT - (time.time() - start_time)
                if timeout <= 0:
                    break
                    
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=timeout
                )
                batch.append(message)
                
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Error collecting batch: {e}")
                break
                
        return batch
        
    async def _process_single_batch(self, batch: List[Dict]):
        """단일 배치 처리"""
        with batch_processing_time.time():
            with self.batch_lock:
                batch_size.set(len(batch))
                active_batches.inc()
                
                try:
                    # 배치 처리 로직 (여기에 실제 배치 처리 구현)
                    logger.info(f"Processing batch of {len(batch)} messages")
                    
                    # 메시지 카운트 업데이트
                    websocket_messages_processed.inc(len(batch))
                    
                    # 배치 처리 완료 후 메트릭 업데이트
                    batch_size.set(0)
                    
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    websocket_errors.inc()
                finally:
                    active_batches.dec()

class ConnectionManager:
    """WebSocket 연결 관리 클래스"""
    
    def __init__(self, batch_processor: BatchProcessor):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, Dict] = {}
        self.batch_processor = batch_processor
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """클라이언트 연결 수락"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0
        }
        
        # 연결 수 메트릭 업데이트
        websocket_connections.inc()
        
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, client_id: str):
        """클라이언트 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_info[client_id]
            
            # 연결 수 메트릭 업데이트
            websocket_connections.dec()
            
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
                websocket_errors.inc()
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
                websocket_errors.inc()
                disconnected_clients.append(client_id)
                
        # 연결이 끊긴 클라이언트 정리
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
    async def process_message_for_batch(self, message_data: Dict, client_id: str):
        """메시지를 배치 처리용으로 큐에 추가"""
        try:
            # 배치 처리용 메시지 데이터 구성
            batch_message = {
                "client_id": client_id,
                "message_data": message_data,
                "timestamp": datetime.now().isoformat(),
                "message_type": message_data.get("type", "chat")
            }
            
            # 배치 큐에 추가
            await self.batch_processor.add_message(batch_message)
            
            # 메시지 처리량 메트릭 업데이트
            websocket_messages_processed.inc()
            
        except Exception as e:
            logger.error(f"Error adding message to batch queue: {e}")
            websocket_errors.inc()
            
    def get_connection_stats(self) -> Dict:
        """연결 통계 반환"""
        return {
            "total_connections": len(self.active_connections),
            "connection_info": self.connection_info,
            "batch_processor_active": self.batch_processor.active if self.batch_processor else False
        }

# 배치 프로세서 및 연결 관리자 인스턴스 생성
batch_processor = BatchProcessor()
manager = ConnectionManager(batch_processor)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명주기 관리"""
    # 시작 시 배치 프로세서 시작
    await batch_processor.start()
    yield
    # 종료 시 배치 프로세서 중지
    await batch_processor.stop()

app = FastAPI(title="WebSocket Chat Server with Batch Processing", lifespan=lifespan)

# Prometheus 메트릭 엔드포인트 추가
app.mount("/metrics", make_asgi_app())

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                
                # 채팅 메시지 처리
                if message_type == "chat":
                    # 배치 처리 큐에 추가
                    await manager.process_message_for_batch(message_data, client_id)
                    
                    # 실시간 브로드캐스트
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
                text_message_data = {
                    "type": "chat",
                    "message": data
                }
                
                # 배치 처리 큐에 추가
                await manager.process_message_for_batch(text_message_data, client_id)
                
                # 실시간 브로드캐스트
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
        websocket_errors.inc()
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
        "connections": len(manager.active_connections),
        "batch_processor_active": batch_processor.active,
        "metrics_available": True
    }

@app.get("/stats")
async def get_stats():
    """연결 통계 엔드포인트"""
    stats = manager.get_connection_stats()
    stats.update({
        "prometheus_metrics": {
            "websocket_connections": websocket_connections._value.get(),
            "websocket_messages_processed": websocket_messages_processed._value.get(),
            "websocket_errors": websocket_errors._value.get()
        }
    })
    return stats

@app.get("/batch-stats")
async def get_batch_stats():
    """배치 처리 통계 엔드포인트"""
    return {
        "batch_size_limit": BATCH_SIZE,
        "batch_timeout": BATCH_TIMEOUT,
        "active": batch_processor.active,
        "metrics": {
            "batch_processing_time": "available",
            "batch_size": "available",
            "active_batches": "available"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)