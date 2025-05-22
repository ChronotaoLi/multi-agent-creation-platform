# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
用于测试PostgreSQL、Redis、Milvus和Neo4j的连通性
"""
import time

def test_postgres():
    """
    测试PostgreSQL连接
    """
    try:
        import psycopg
        print("正在连接PostgreSQL...")
        
        # 创建连接
        conn = psycopg.connect(
            "host=localhost port=5432 dbname=ai_creation user=postgres password=postgres"
        )
        
        # 验证连接
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        print("✅ PostgreSQL连接成功！")
        print(f"PostgreSQL版本: {version[0]}")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL连接失败: {str(e)}")
        return False

def test_redis():
    """
    测试Redis连接
    """
    try:
        import redis
        print("正在连接Redis...")
        
        # 创建连接
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        # 验证连接
        info = r.info()
        
        print("✅ Redis连接成功！")
        print(f"Redis版本: {info['redis_version']}")
        return True
        
    except Exception as e:
        print(f"❌ Redis连接失败: {str(e)}")
        return False

def test_milvus():
    """
    测试Milvus连接
    """
    try:
        from pymilvus import connections, utility
        print("正在连接Milvus...")
        
        # 创建连接
        connections.connect(
            alias="default", 
            host="localhost", 
            port="19530"
        )
        
        # 验证连接
        status = utility.get_server_version()
        
        print("✅ Milvus连接成功！")
        print(f"Milvus版本: {status}")
        return True
        
    except Exception as e:
        print(f"❌ Milvus连接失败: {str(e)}")
        return False

def test_neo4j():
    """
    测试Neo4j连接
    """
    try:
        from neo4j import GraphDatabase
        print("正在连接Neo4j...")
        
        # 创建连接
        driver = GraphDatabase.driver(
            "bolt://localhost:7687", 
            auth=("neo4j", "password")
        )
        
        # 验证连接
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS count")
            count = result.single()["count"]
        
        # 关闭连接
        driver.close()
        
        print("✅ Neo4j连接成功！")
        print(f"Neo4j数据库中节点数量: {count}")
        return True
        
    except Exception as e:
        print(f"❌ Neo4j连接失败: {str(e)}")
        return False

def main():
    """
    主函数，测试所有数据库连接
    """
    print("=== 数据库连通性测试开始 ===")
    print()
    
    # 测试PostgreSQL
    pg_result = test_postgres()
    print()
    
    # 等待一秒钟
    time.sleep(1)
    
    # 测试Redis
    redis_result = test_redis()
    print()
    
    # 等待一秒钟
    time.sleep(1)
    
    # 测试Milvus
    milvus_result = test_milvus()
    print()
    
    # 等待一秒钟
    time.sleep(1)
    
    # 测试Neo4j
    neo4j_result = test_neo4j()
    print()
    
    # 总结
    print("=== 连通性测试结果摘要 ===")
    print(f"PostgreSQL: {'成功 ✅' if pg_result else '失败 ❌'}")
    print(f"Redis: {'成功 ✅' if redis_result else '失败 ❌'}")
    print(f"Milvus: {'成功 ✅' if milvus_result else '失败 ❌'}")
    print(f"Neo4j: {'成功 ✅' if neo4j_result else '失败 ❌'}")
    
    if pg_result and redis_result and milvus_result and neo4j_result:
        print("\n🎉 所有数据库连接测试通过！")
    else:
        print("\n⚠️ 部分数据库连接测试失败，请检查上面的具体错误信息。")

if __name__ == "__main__":
    main()