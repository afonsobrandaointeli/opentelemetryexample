package soma.api;

import io.micronaut.context.annotation.Context;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Context
public class LoggingService {
    
    private static final Logger log = LoggerFactory.getLogger(LoggingService.class);
    private static final String DB_URL = "jdbc:sqlite:soma_logs.db";

    @PostConstruct
    public void initialize() {
        log.info("=== INITIALIZING LOGGING SERVICE ===");
        try {
            createTables();
            log.info("=== LOGGING SERVICE INITIALIZED SUCCESSFULLY ===");
        } catch (Exception e) {
            log.error("=== FAILED TO INITIALIZE LOGGING SERVICE ===", e);
        }
    }

    private void createTables() {
        try (Connection conn = DriverManager.getConnection(DB_URL);
             Statement stmt = conn.createStatement()) {
            
            log.info("Creating tables in database: {}", DB_URL);
            
            // Tabela de operações (existente)
            String createOperationsTable = """
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    operation_type TEXT,
                    input_a INTEGER,
                    input_b INTEGER,
                    result INTEGER,
                    execution_time_ms BIGINT,
                    trace_id TEXT,
                    span_id TEXT
                )
            """;

            // Nova tabela de logs de negócio
            String createBusinessLogsTable = """
                CREATE TABLE IF NOT EXISTS business_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT,
                    user_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    hour_of_day INTEGER,
                    day_period TEXT,
                    operation_type TEXT,
                    input_values TEXT,
                    result_value INTEGER,
                    execution_time_ms BIGINT,
                    trace_id TEXT,
                    ip_address TEXT,
                    status TEXT,
                    message TEXT,
                    FOREIGN KEY (operation_id) REFERENCES operations(id)
                )
            """;

            stmt.execute(createOperationsTable);
            stmt.execute(createBusinessLogsTable);
            
            log.info("All tables created/verified successfully");
            
        } catch (SQLException e) {
            log.error("Failed to create tables", e);
            throw new RuntimeException("Database initialization failed", e);
        }
    }

    public void logOperation(String operationId, String operationType, int a, int b, int result, 
                           long executionTime, String traceId, String spanId) {
        
        try (Connection conn = DriverManager.getConnection(DB_URL);
             PreparedStatement pstmt = conn.prepareStatement(
                 "INSERT INTO operations (id, operation_type, input_a, input_b, result, execution_time_ms, trace_id, span_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")) {
            
            pstmt.setString(1, operationId);
            pstmt.setString(2, operationType);
            pstmt.setInt(3, a);
            pstmt.setInt(4, b);
            pstmt.setInt(5, result);
            pstmt.setLong(6, executionTime);
            pstmt.setString(7, traceId);
            pstmt.setString(8, spanId);
            
            pstmt.executeUpdate();
            log.info("Operation logged successfully: {} + {} = {}", a, b, result);
            
        } catch (SQLException e) {
            log.error("Failed to log operation to database", e);
        }
    }

    public void logBusinessOperation(String operationId, String userId, String operationType, 
                                   int inputA, int inputB, int result, long executionTime, 
                                   String traceId, String ipAddress) {
        
        LocalDateTime now = LocalDateTime.now();
        int hourOfDay = now.getHour();
        String dayPeriod = getDayPeriod(hourOfDay);
        String inputValues = String.format("%d + %d", inputA, inputB);
        
        try (Connection conn = DriverManager.getConnection(DB_URL);
             PreparedStatement pstmt = conn.prepareStatement("""
                 INSERT INTO business_logs 
                 (operation_id, user_id, hour_of_day, day_period, operation_type, 
                  input_values, result_value, execution_time_ms, trace_id, ip_address, status, message) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
             """)) {
            
            pstmt.setString(1, operationId);
            pstmt.setString(2, userId);
            pstmt.setInt(3, hourOfDay);
            pstmt.setString(4, dayPeriod);
            pstmt.setString(5, operationType);
            pstmt.setString(6, inputValues);
            pstmt.setInt(7, result);
            pstmt.setLong(8, executionTime);
            pstmt.setString(9, traceId);
            pstmt.setString(10, ipAddress);
            pstmt.setString(11, "SUCCESS");
            pstmt.setString(12, String.format("User %s performed %s operation: %s = %d", 
                                            userId, operationType, inputValues, result));
            
            pstmt.executeUpdate();
            
            log.info("Business log created: User {} performed {} at {} ({})", 
                    userId, inputValues, now.format(DateTimeFormatter.ofPattern("HH:mm:ss")), dayPeriod);
            
        } catch (SQLException e) {
            log.error("Failed to log business operation", e);
        }
    }

    private String getDayPeriod(int hour) {
        if (hour >= 6 && hour < 12) {
            return "MORNING";
        } else if (hour >= 12 && hour < 18) {
            return "AFTERNOON";
        } else if (hour >= 18 && hour < 22) {
            return "EVENING";
        } else {
            return "NIGHT";
        }
    }
}