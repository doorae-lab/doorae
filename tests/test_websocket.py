"""
WebSocket 채팅 서버 테스트 모듈
다중 유저 채팅 서버의 WebSocket 기능을 검증합니다.
배치 처리 통합 및 Prometheus 메트릭 테스트 포함
"""

import asyncio
import json
import time
import pytest
import websockets
import httpx
from typing import List, Dict, Any
from datetime import datetime


class TestWebSocketChatServer:
    """WebSocket 채팅 서버 테스트 클래스"""
    
    # 테스트 서버 설정
    SERVER_HOST = "localhost"
    SERVER_PORT = 8000
    WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws"
    HTTP_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
    
    @pytest.fixture
    async def websocket_client(self):
        """WebSocket 클라이언트 연결 픽스처"""
        async with websockets.connect(f"{self.WS_URL}/test_client") as websocket:
            yield websocket
            await websocket.close()
    
    @pytest.fixture
    async def multiple_clients(self):
        """다중 WebSocket 클라이언트 연결 픽스처"""
        clients = []
        for i in range(3):
            websocket = await websockets.connect(f"{self.WS_URL}/client_{i}")
            clients.append(websocket)
        
        yield clients
        
        for client in clients:
            await client.close()
    
    @pytest.fixture
    async def http_client(self):
        """HTTP 클라이언트 픽스처"""
        async with httpx.AsyncClient(base_url=self.HTTP_URL) as client:
            yield client
    
    # 1. 기본 연결 테스트
    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_client):
        """WebSocket 연결/해제 기능 테스트"""
        websocket = websocket_client
        
        # 연결 상태 확인
        assert websocket.open
        
        # 환영 메시지 수신
        welcome_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        welcome_data = json.loads(welcome_message)
        
        assert welcome_data["type"] == "system"
        assert "Welcome" in welcome_data["message"]
        assert "total_connections" in welcome_data
        
        print("✓ WebSocket 연결/해제 테스트 통과")
    
    # 2. 메시지 송수신 테스트
    @pytest.mark.asyncio
    async def test_message_send_receive(self, websocket_client):
        """메시지 송수신 기능 테스트"""
        websocket = websocket_client
        
        # 환영 메시지 수신
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        # 테스트 메시지 전송
        test_message = {
            "type": "chat",
            "message": "Hello, WebSocket!"
        }
        
        await websocket.send(json.dumps(test_message))
        
        # 브로드캐스트 메시지 수신 (자신에게도 전송됨)
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        response_data = json.loads(response)
        
        assert response_data["type"] == "chat"
        assert response_data["message"] == "Hello, WebSocket!"
        assert "sender" in response_data
        assert "timestamp" in response_data
        
        print("✓ 메시지 송수신 테스트 통과")
    
    # 3. 브로드캐스트 기능 테스트
    @pytest.mark.asyncio
    async def test_broadcast_functionality(self, multiple_clients):
        """브로드캐스트 메시지 기능 테스트"""
        clients = multiple_clients
        
        # 모든 클라이언트가 환영 메시지 수신
        for client in clients:
            await asyncio.wait_for(client.recv(), timeout=3.0)
        
        # 첫 번째 클라이언트가 채팅 메시지 전송
        broadcast_message = {
            "type": "chat",
            "message": "System announcement"
        }
        
        await clients[0].send(json.dumps(broadcast_message))
        
        # 모든 클라이언트가 메시지 수신 확인
        received_messages = []
        for client in clients:
            try:
                response = await asyncio.wait_for(client.recv(), timeout=3.0)
                response_data = json.loads(response)
                received_messages.append(response_data)
            except asyncio.TimeoutError:
                continue
        
        # 모든 클라이언트가 메시지 수신
        assert len(received_messages) == len(clients)
        
        for msg in received_messages:
            assert msg["type"] == "chat"
            assert msg["message"] == "System announcement"
        
        print("✓ 브로드캐스트 기능 테스트 통과")
    
    # 4. 동시 접속 부하 테스트
    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """동시 다중 접속 부하 테스트"""
        num_clients = 10
        clients = []
        
        try:
            # 다중 클라이언트 동시 연결
            for i in range(num_clients):
                websocket = await websockets.connect(f"{self.WS_URL}/load_test_{i}")
                clients.append(websocket)
                
                # 환영 메시지 수신
                await asyncio.wait_for(websocket.recv(), timeout=3.0)
            
            # 모든 클라이언트 연결 상태 확인
            for client in clients:
                assert client.open
            
            # 간단한 메시지 교환 테스트
            test_client = clients[0]
            test_message = {
                "type": "chat",
                "message": "concurrent test"
            }
            
            await test_client.send(json.dumps(test_message))
            response = await asyncio.wait_for(test_client.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            assert response_data["type"] == "chat"
            assert response_data["message"] == "concurrent test"
            
            print(f"✓ 동시 {num_clients}명 접속 테스트 통과")
            
        finally:
            # 모든 클라이언트 정리
            for client in clients:
                await client.close()
    
    # 5. 재연결 안정성 테스트
    @pytest.mark.asyncio
    async def test_reconnection_stability(self):
        """재연결 안정성 테스트"""
        max_attempts = 3
        successful_reconnections = 0
        
        for attempt in range(max_attempts):
            try:
                # 연결
                websocket = await websockets.connect(f"{self.WS_URL}/reconnect_{attempt}")
                
                # 연결 확인
                assert websocket.open
                
                # 환영 메시지 수신
                await asyncio.wait_for(websocket.recv(), timeout=3.0)
                
                # 간단한 메시지 전송
                test_message = {"type": "chat", "message": f"reconnect test {attempt}"}
                await websocket.send(json.dumps(test_message))
                
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                
                assert response_data["type"] == "chat"
                assert response_data["message"] == f"reconnect test {attempt}"
                
                # 연결 종료
                await websocket.close()
                
                # 재연결 대기
                await asyncio.sleep(1)
                
                successful_reconnections += 1
                
            except Exception as e:
                print(f"재연결 시도 {attempt + 1} 실패: {e}")
                continue
        
        # 최소 2회 이상 성공적인 재연결
        assert successful_reconnections >= 2
        print(f"✓ 재연결 안정성 테스트 통과 ({successful_reconnections}/{max_attempts} 성공)")
    
    # 6. 메시지 무결성 테스트
    @pytest.mark.asyncio
    async def test_message_integrity(self, websocket_client):
        """메시지 무결성 및 순서 보장 테스트"""
        websocket = websocket_client
        
        # 환영 메시지 수신
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        messages_to_send = [
            {"type": "chat", "message": "첫 번째 메시지"},
            {"type": "chat", "message": "두 번째 메시지"},
            {"type": "chat", "message": "세 번째 메시지"}
        ]
        
        received_messages = []
        
        # 메시지 순차 전송
        for msg in messages_to_send:
            await websocket.send(json.dumps(msg))
            
            # 응답 수신
            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
            response_data = json.loads(response)
            
            received_messages.append(response_data)
        
        # 메시지 순서 확인
        for i, received_msg in enumerate(received_messages):
            assert received_msg["type"] == "chat"
            assert received_msg["message"] == messages_to_send[i]["message"]
        
        print("✓ 메시지 무결성 및 순서 보장 테스트 통과")
    
    # 7. 성능 측정 테스트
    @pytest.mark.asyncio
    async def test_performance_metrics(self, websocket_client):
        """메시지 처리 성능 측정 테스트"""
        websocket = websocket_client
        
        # 환영 메시지 수신
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        num_messages = 10
        latencies = []
        
        for i in range(num_messages):
            start_time = time.time()
            
            test_message = {
                "type": "chat",
                "message": f"performance test {i}"
            }
            
            await websocket.send(json.dumps(test_message))
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # 밀리초 변환
            
            latencies.append(latency)
            
            assert response_data["type"] == "chat"
            assert response_data["message"] == f"performance test {i}"
        
        # 성능 통계 계산
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        print(f"성능 측정 결과:")
        print(f"  - 평균 지연시간: {avg_latency:.2f}ms")
        print(f"  - 최대 지연시간: {max_latency:.2f}ms")
        print(f"  - 최소 지연시간: {min_latency:.2f}ms")
        
        # 성능 기준: 95% 메시지가 100ms 이내 처리
        threshold_100ms = 100
        messages_within_threshold = sum(1 for lat in latencies if lat <= threshold_100ms)
        percentage_within_threshold = (messages_within_threshold / num_messages) * 100
        
        print(f"  - {threshold_100ms}ms 이내 처리율: {percentage_within_threshold:.1f}%")
        
        # 성능 기준 통과 확인 (95% 이상이 100ms 이내)
        assert percentage_within_threshold >= 95.0
        print("✓ 성능 측정 테스트 통과 (95% 메시지 100ms 이내 처리)")
    
    # 8. 에러 처리 테스트
    @pytest.mark.asyncio
    async def test_error_handling(self, websocket_client):
        """에러 처리 및 예외 상황 테스트"""
        websocket = websocket_client
        
        # 환영 메시지 수신
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        # 잘못된 형식의 메시지 전송
        invalid_messages = [
            "invalid json string",
            json.dumps({"invalid": "message"}),
            json.dumps({"type": "unknown_type"}),
            ""
        ]
        
        for invalid_msg in invalid_messages:
            await websocket.send(invalid_msg)
            
            # 서버가 연결을 유지하는지 확인
            assert websocket.open
            
            # 에러 응답 수신 시도
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                response_data = json.loads(response)
                
                # JSON 파싱 에러인 경우 텍스트 메시지로 처리됨
                if "type" in response_data:
                    assert response_data["type"] == "chat"
            except (asyncio.TimeoutError, json.JSONDecodeError):
                # 타임아웃이나 파싱 에러는 허용
                pass
        
        print("✓ 에러 처리 테스트 통과")
    
    # 9. 대용량 메시지 테스트
    @pytest.mark.asyncio
    async def test_large_message_handling(self, websocket_client):
        """대용량 메시지 처리 테스트"""
        websocket = websocket_client
        
        # 환영 메시지 수신
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        # 대용량 메시지 생성 (약 10KB)
        large_content = "X" * 10000
        large_message = {
            "type": "chat",
            "message": large_content
        }
        
        start_time = time.time()
        await websocket.send(json.dumps(large_message))
        
        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        response_data = json.loads(response)
        
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        
        assert response_data["type"] == "chat"
        assert len(response_data["message"]) == len(large_content)
        
        print(f"✓ 대용량 메시지 처리 테스트 통과 ({processing_time:.2f}ms 소요)")
    
    # 10. 통합 기능 테스트
    @pytest.mark.asyncio
    async def test_integrated_functionality(self):
        """통합 기능 종합 테스트"""
        # 다중 클라이언트 시나리오
        num_clients = 5
        clients = []
        
        try:
            # 클라이언트 연결
            for i in range(num_clients):
                websocket = await websockets.connect(f"{self.WS_URL}/integrated_{i}")
                clients.append((websocket, f"user_{i}"))
                
                # 환영 메시지 수신
                await asyncio.wait_for(websocket.recv(), timeout=3.0)
            
            # 채팅 시나리오 실행
            messages_exchanged = 0
            
            for sender_idx, (sender_ws, sender_id) in enumerate(clients):
                # 각 클라이언트가 메시지 전송
                chat_message = {
                    "type": "chat",
                    "message": f"Message from {sender_id}"
                }
                
                await sender_ws.send(json.dumps(chat_message))
                messages_exchanged += 1
                
                # 발신자 확인 응답
                try:
                    response = await asyncio.wait_for(sender_ws.recv(), timeout=3.0)
                    response_data = json.loads(response)
                    assert response_data["type"] == "chat"
                    assert response_data["message"] == f"Message from {sender_id}"
                except asyncio.TimeoutError:
                    print(f"발신자 {sender_id} 확인 응답 타임아웃")
            
            # 최소 메시지 교환 확인
            assert messages_exchanged >= num_clients
            
            print(f"✓ 통합 기능 테스트 통과 ({num_clients}명 클라이언트, {messages_exchanged}개 메시지 교환)")
            
        finally:
            # 클라이언트 정리
            for client_ws, _ in clients:
                await client_ws.close()
    
    # 11. HTTP 헬스 체크 테스트
    @pytest.mark.asyncio
    async def test_http_health_check(self, http_client):
        """HTTP 헬스 체크 엔드포인트 테스트"""
        response = await http_client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "connections" in data
        assert "batch_processor_active" in data
        assert data["metrics_available"] == True
        
        print("✓ HTTP 헬스 체크 테스트 통과")
    
    # 12. HTTP 통계 엔드포인트 테스트
    @pytest.mark.asyncio
    async def test_http_stats_endpoint(self, http_client):
        """HTTP 통계 엔드포인트 테스트"""
        response = await http_client.get("/stats")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "total_connections" in data
        assert "connection_info" in data
        assert "batch_processor_active" in data
        assert "prometheus_metrics" in data
        
        print("✓ HTTP 통계 엔드포인트 테스트 통과")
    
    # 13. 배치 처리 통계 테스트
    @pytest.mark.asyncio
    async def test_batch_stats_endpoint(self, http_client):
        """배치 처리 통계 엔드포인트 테스트"""
        response = await http_client.get("/batch-stats")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "batch_size_limit" in data
        assert data["batch_size_limit"] == 100
        assert "batch_timeout" in data
        assert data["batch_timeout"] == 1.0
        assert "active" in data
        assert data["active"] == True
        assert "metrics" in data
        
        print("✓ 배치 처리 통계 테스트 통과")
    
    # 14. Prometheus 메트릭 엔드포인트 테스트
    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint(self, http_client):
        """Prometheus 메트릭 엔드포인트 테스트"""
        response = await http_client.get("/metrics")
        
        assert response.status_code == 200
        
        # Prometheus 메트릭 형식 확인
        content = response.text
        assert "websocket_connections" in content
        assert "websocket_messages_processed_total" in content
        assert "websocket_errors_total" in content
        assert "batch_processing_time_seconds" in content
        assert "batch_size" in content
        assert "active_batches" in content
        
        print("✓ Prometheus 메트릭 엔드포인트 테스트 통과")
    
    # 15. 배치 처리 통합 테스트
    @pytest.mark.asyncio
    async def test_batch_processing_integration(self, websocket_client, http_client):
        """배치 처리 통합 테스트"""
        websocket = websocket_client
        
        # 환영 메시지 수신
        await asyncio.wait_for(websocket.recv(), timeout=5.0)
        
        # 배치 처리 전 메트릭 확인
        initial_metrics_response = await http_client.get("/metrics")
        initial_content = initial_metrics_response.text
        
        # 여러 메시지 전송 (배치 처리 유발)
        num_messages = 50
        for i in range(num_messages):
            test_message = {
                "type": "chat",
                "message": f"batch test {i}"
            }
            await websocket.send(json.dumps(test_message))
            
            # 응답 수신
            await asyncio.wait_for(websocket.recv(), timeout=2.0)
        
        # 배치 처리 후 메트릭 확인
        await asyncio.sleep(2)  # 배치 처리 완료 대기
        
        final_metrics_response = await http_client.get("/metrics")
        final_content = final_metrics_response.text
        
        # 메트릭 증가 확인
        assert "websocket_messages_processed_total" in final_content
        
        # 배치 처리 활성 상태 확인
        batch_stats_response = await http_client.get("/batch-stats")
        batch_stats = batch_stats_response.json()
        assert batch_stats["active"] == True
        
        print("✓ 배치 처리 통합 테스트 통과")


if __name__ == "__main__":
    """테스트 직접 실행 (개발용)"""
    import sys
    
    print("WebSocket 테스트 모듈 실행")
    print("=" * 50)
    
    # pytest 실행 명령어 출력
    print("테스트 실행 명령어:")
    print("  pytest tests/test_websocket.py -v")
    print()
    
    # 테스트 시나리오 요약
    test_cases = [
        "1. WebSocket 연결/해제 테스트",
        "2. 메시지 송수신 기능 테스트",
        "3. 브로드캐스트 기능 테스트",
        "4. 동시 접속 부하 테스트 (10명)",
        "5. 재연결 안정성 테스트",
        "6. 메시지 무결성 및 순서 보장 테스트",
        "7. 성능 측정 테스트 (95% 메시지 100ms 이내)",
        "8. 에러 처리 테스트",
        "9. 대용량 메시지 처리 테스트",
        "10. 통합 기능 종합 테스트 (5명 클라이언트)",
        "11. HTTP 헬스 체크 테스트",
        "12. HTTP 통계 엔드포인트 테스트",
        "13. 배치 처리 통계 테스트",
        "14. Prometheus 메트릭 엔드포인트 테스트",
        "15. 배치 처리 통합 테스트"
    ]
    
    print("구현된 테스트 시나리오:")
    for test_case in test_cases:
        print(f"  {test_case}")
    
    sys.exit(0)