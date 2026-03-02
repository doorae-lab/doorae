# Circuit Breaker 설계 문서

## 1. 개요
LLM 노드 실패 시 전체 시스템 중단을 방지하기 위한 Circuit Breaker 패턴 구현 설계 문서입니다.

## 2. 요구사항
- #156 이슈: 개별 LLM 노드 실패 시 전체 시스템 중단 방지
- 실시간 상태 모니터링 및 UI 표시
- 자동 복구 메커니즘
- 히스토리 로깅 및 분석

## 3. 아키텍처

### 3.1 Circuit Breaker 상태 머신
```
CLOSED → (실패 임계값 초과) → OPEN → (timeout 경과) → HALF_OPEN → (성공) → CLOSED
                                                      ↓ (실패) → OPEN
```

### 3.2 구성 요소
1. **Circuit Breaker Manager**: 노드별 Circuit Breaker 인스턴스 관리
2. **상태 모니터**: 실시간 상태 감시 및 이벤트 발생
3. **이벤트 브로커**: WebSocket을 통한 실시간 상태 전파
4. **로깅 시스템**: PostgreSQL 기반 히스토리 저장

## 4. 상태 정의

### 4.1 상태 값
- **CLOSED**: 정상 동작 (요청 허용)
- **OPEN**: 회로 개방 (요청 차단, fallback 사용)
- **HALF_OPEN**: 제한적 테스트 (일부 요청 허용)

### 4.2 상태 전이 조건
- **CLOSED → OPEN**: 연속 실패 횟수 > `failure_threshold` (기본값: 5)
- **OPEN → HALF_OPEN**: `timeout` 경과 (기본값: 30초)
- **HALF_OPEN → CLOSED**: 테스트 요청 성공
- **HALF_OPEN → OPEN**: 테스트 요청 실패

## 5. WebSocket 이벤트 포맷

### 5.1 기본 이벤트 구조
```json
{
  "type": "circuit_breaker_status",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "node_id": "llm-node-1",
    "status": "OPEN",
    "previous_status": "CLOSED",
    "circuit_breaker_id": "cb-llm-node-1",
    "retry_after": 30,
    "failure_count": 5,
    "fallback_used": true,
    "error_message": "Connection timeout after 5000ms",
    "metadata": {
      "event_id": "event-123456",
      "source": "circuit-breaker-manager"
    }
  }
}
```

### 5.2 이벤트 타입
- `circuit_breaker_status`: 상태 변경 이벤트
- `circuit_breaker_health`: 주기적 헬스체크 이벤트
- `circuit_breaker_summary`: 전체 시스템 요약 이벤트

## 6. 설정 파라미터

### 6.1 기본 설정
```yaml
circuit_breaker:
  failure_threshold: 5
  timeout: 30000  # milliseconds
  success_threshold: 3
  half_open_max_requests: 1
  sliding_window_size: 10
```

### 6.2 노드별 오버라이드 가능
```yaml
llm-node-1:
  failure_threshold: 3  # 민감한 노드
  timeout: 60000        # 긴 타임아웃
```

## 7. Fallback 전략

### 7.1 Fallback 계층
1. **동일 유형 대체 노드**: 동일 LLM 제공자 다른 엔드포인트
2. **다른 유형 노드**: 다른 LLM 제공자
3. **캐시 응답**: 최근 성공 응답 재사용
4. **기본 응답**: 시스템 기본 응답 반환

### 7.2 Fallback 메타데이터
```json
{
  "fallback_used": true,
  "fallback_type": "alternative_node",
  "fallback_target": "llm-node-2",
  "original_node": "llm-node-1"
}
```

## 8. 모니터링 및 알림

### 8.1 Redis Pub/Sub 알림 채널
- `circuit-breaker:status`: 상태 변경 알림
- `circuit-breaker:alert`: 긴급 알림 (다수 노드 실패)

### 8.2 알림 수준
- **INFO**: 상태 변경 (CLOSED ↔ OPEN)
- **WARNING**: HALF_OPEN 상태
- **ERROR**: 연속 실패 또는 다수 노드 실패

## 9. 데이터베이스 스키마

### 9.1 circuit_breaker_events 테이블
```sql
CREATE TABLE circuit_breaker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id VARCHAR(100) NOT NULL,
    circuit_breaker_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    previous_status VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms INTEGER,
    failure_count INTEGER,
    error_message TEXT,
    fallback_used BOOLEAN DEFAULT FALSE,
    fallback_type VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_circuit_breaker_events_node_id ON circuit_breaker_events(node_id);
CREATE INDEX idx_circuit_breaker_events_timestamp ON circuit_breaker_events(timestamp);
CREATE INDEX idx_circuit_breaker_events_status ON circuit_breaker_events(status);
```

### 9.2 circuit_breaker_stats 테이블
```sql
CREATE TABLE circuit_breaker_stats (
    node_id VARCHAR(100) PRIMARY KEY,
    total_requests BIGINT DEFAULT 0,
    failed_requests BIGINT DEFAULT 0,
    total_open_time_ms BIGINT DEFAULT 0,
    last_status VARCHAR(20),
    last_status_change TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 10. API 엔드포인트

### 10.1 상태 조회
- `GET /api/v1/circuit-breakers`: 전체 노드 상태
- `GET /api/v1/circuit-breakers/{node_id}`: 특정 노드 상태
- `GET /api/v1/circuit-breakers/{node_id}/history`: 히스토리 조회

### 10.2 히스토리 조회 응답 구조
```json
{
  "node_id": "llm-node-1",
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-01T01:00:00Z"
  },
  "events": [
    {
      "timestamp": "2024-01-01T00:05:00Z",
      "status": "OPEN",
      "duration_ms": 30000,
      "error_message": "Connection timeout",
      "circuit_breaker_id": "cb-llm-node-1",
      "failure_count": 5,
      "fallback_used": true
    }
  ],
  "statistics": {
    "total_open_time_ms": 120000,
    "open_count": 4,
    "avg_recovery_time_ms": 45000,
    "success_rate": 0.95
  }
}
```

## 11. 구현 일정

### 11.1 Phase 1: 기본 구조 (1주)
- Circuit Breaker Manager 구현
- 상태 머신 로직 구현
- 기본 설정 관리

### 11.2 Phase 2: 통합 및 테스트 (1주)
- LLM 노드 통합
- 단위/통합 테스트
- E2E 테스트 시나리오

### 11.3 Phase 3: 모니터링 및 UI (1주)
- WebSocket 이벤트 시스템
- UI 컴포넌트 연동
- 히스토리 로깅 시스템

## 12. 테스트 전략

### 12.1 단위 테스트
- 상태 전이 로직
- 설정 파라미터 검증
- Fallback 메커니즘

### 12.2 통합 테스트
- 실제 LLM 노드 연동 테스트
- Redis Pub/Sub 알림 테스트
- PostgreSQL 로깅 테스트

### 12.3 E2E 테스트
- 전체 시스템 장애 시나리오
- 복구 프로세스 검증
- UI 상태 표시 테스트

## 13. 성능 고려사항

### 13.1 부하 분산
- Circuit Breaker 인스턴스별 메모리 사용량 최적화
- 이벤트 브로커 병목 현상 방지
- 데이터베이스 인덱스 최적화

### 13.2 확장성
- 노드 추가 시 자동 Circuit Breaker 생성
- 설정 동적 변경 지원
- 모니터링 대시보드 확장

---

**문서 버전**: 1.0  
**최종 업데이트**: 2024-01-01  
**담당자**: TechLead