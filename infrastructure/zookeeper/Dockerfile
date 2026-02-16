# Dockerfile for Zookeeper (to install netcat for healthcheck)
FROM confluentinc/cp-zookeeper:7.2.1

USER root
RUN yum update -y && yum install -y procps && yum clean all
