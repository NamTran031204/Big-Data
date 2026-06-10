# Stage 1: Build
# Dùng image Maven chính thức để không cần mvnw hay cài Maven riêng
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app

# Copy pom.xml riêng để Docker cache layer dependency (rebuild nhanh khi chỉ đổi source)
COPY pom.xml .
RUN mvn dependency:go-offline -q

COPY src/ src/
RUN mvn package -DskipTests -q

# Stage 2: Runtime (JRE nhỏ hơn JDK ~200MB)
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8085
ENTRYPOINT ["java", "-jar", "app.jar"]
