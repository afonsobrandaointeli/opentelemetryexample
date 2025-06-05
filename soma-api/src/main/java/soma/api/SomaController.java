package soma.api;

import io.micronaut.http.HttpRequest;
import io.micronaut.http.annotation.*;
import io.micronaut.serde.annotation.Serdeable;
import io.micronaut.tracing.annotation.NewSpan;
import io.micronaut.tracing.annotation.SpanTag;
import io.opentelemetry.api.trace.Span;
import jakarta.inject.Inject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.UUID;

@Controller("/soma")
public class SomaController {

    private static final Logger log = LoggerFactory.getLogger(SomaController.class);
    
    private final LoggingService loggingService;

    public SomaController(LoggingService loggingService) {
        this.loggingService = loggingService;
        log.info("SomaController initialized with LoggingService");
    }

    @Get("/{a}/{b}")
    @NewSpan("soma-operation")
    public SomaResponse soma(@SpanTag("input.a") int a, 
                            @SpanTag("input.b") int b,
                            @QueryValue(value = "user_id", defaultValue = "anonymous") String userId,
                            HttpRequest<?> request) {
        
        String operationId = UUID.randomUUID().toString();
        long startTime = System.currentTimeMillis();
        
        // Obter informações do span atual
        Span currentSpan = Span.current();
        String traceId = currentSpan.getSpanContext().getTraceId();
        String spanId = currentSpan.getSpanContext().getSpanId();
        
        // Obter IP do cliente
        String clientIp = getClientIpAddress(request);
        
        log.info("Starting sum operation: {} + {} (Operation ID: {}, User: {}, IP: {})", 
                a, b, operationId, userId, clientIp);
        
        // Adicionar atributos ao span
        currentSpan.setAttribute("operation.id", operationId);
        currentSpan.setAttribute("operation.type", "sum");
        currentSpan.setAttribute("user.id", userId);
        currentSpan.setAttribute("client.ip", clientIp);
        
        try {
            int result = a + b;
            long executionTime = System.currentTimeMillis() - startTime;
            
            // Log técnico (tabela operations)
            loggingService.logOperation(operationId, "sum", a, b, result, executionTime, traceId, spanId);
            
            // Log de negócio (tabela business_logs)
            loggingService.logBusinessOperation(operationId, userId, "sum", a, b, result, 
                                              executionTime, traceId, clientIp);
            
            // Adicionar resultado ao span
            currentSpan.setAttribute("operation.result", result);
            currentSpan.setAttribute("operation.execution_time_ms", executionTime);
            
            log.info("Sum operation completed: {} + {} = {} ({}ms) for user {}", 
                    a, b, result, executionTime, userId);
            
            return new SomaResponse(operationId, a, b, result, executionTime, userId, traceId);
            
        } catch (Exception e) {
            currentSpan.recordException(e);
            currentSpan.setStatus(io.opentelemetry.api.trace.StatusCode.ERROR, e.getMessage());
            
            log.error("Sum operation failed for user {}", userId, e);
            throw new RuntimeException("Calculation failed", e);
        }
    }

    private String getClientIpAddress(HttpRequest<?> request) {
        // Tentar obter o IP real através de headers de proxy
        String xForwardedFor = request.getHeaders().get("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        
        String xRealIp = request.getHeaders().get("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }
        
        // Fallback para IP direto
        return request.getRemoteAddress().getAddress().getHostAddress();
    }

    // Classe de resposta anotada com @Serdeable
    @Serdeable
    public static class SomaResponse {
        private final String operationId;
        private final int inputA;
        private final int inputB;
        private final int result;
        private final long executionTimeMs;
        private final String userId;
        private final String traceId;

        public SomaResponse(String operationId, int inputA, int inputB, int result, 
                           long executionTimeMs, String userId, String traceId) {
            this.operationId = operationId;
            this.inputA = inputA;
            this.inputB = inputB;
            this.result = result;
            this.executionTimeMs = executionTimeMs;
            this.userId = userId;
            this.traceId = traceId;
        }

        // Getters obrigatórios para serialização
        public String getOperationId() { return operationId; }
        public int getInputA() { return inputA; }
        public int getInputB() { return inputB; }
        public int getResult() { return result; }
        public long getExecutionTimeMs() { return executionTimeMs; }
        public String getUserId() { return userId; }
        public String getTraceId() { return traceId; }
    }
}