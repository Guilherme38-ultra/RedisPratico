import os

import psycopg2
import redis
from dotenv import load_dotenv

load_dotenv()

r = redis.Redis(host="localhost", port=6379, db=10, decode_responses=True)

DATABASE_URL = os.getenv("DATABASE_URL")

CACHE_TTL = 60

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def buscar_produto(id_produto, cursor):
    chave = f"produto:{id_produto}"

    if r.exists(chave):
        print("Produto carregado do cache (Redis - HASH).")
        produto = r.hgetall(chave)

    else:
        print("Produto não está no cache. Buscando no banco de dados...")
        cursor.execute("select nome, preco from produtos WHERE id = %s", (id_produto,))
        resultado = cursor.fetchone()
        if not resultado:
            print("Produto não encontrado no banco.")
            return

        nome, preco = resultado

        r.hset(
            chave, mapping={
                "nome": nome, 
                "preco": str(preco)
                }
            )

        r.expire(chave, CACHE_TTL)

        print(f"Produto salvo no cache com TTL de {CACHE_TTL} segundos.")

        produto = {
            "nome": nome,
            "preco": str(preco)
        }

    print(
        f"Produto: {produto['nome']} - "
        f"R$ {float(produto['preco']):.2f}"
    )

def listar_chaves_produtos():
    print("\nChaves de produtos presentes no Redis:")

    cursor_redis = 0
    encontrou = False

    while True:
        cursor_redis, chaves = r.scan(cursor=cursor_redis,match="produto:*",count=100)

        for chave in chaves:
            produto = r.hgetall(chave)

            if produto:
                print(f"\n{chave}")

                for campo, valor in produto.items():
                    print(f"  {campo}: {valor}")

                encontrou = True

        if cursor_redis == 0:
            break

    if not encontrou:
        print("Nenhum produto encontrado no cache.")

def menu():
    conn = get_conn()
    cursor = conn.cursor()

    try:
        while True:
            print("\n--- MENU DE CONSULTA DE PRODUTOS ---")
            print("1. Buscar um produto")
            print("2. Listar as chaves dos produtos")
            print("3. Sair")

            escolha = input("Escolha um opção: ")

            if escolha == "1":
                id_produto = input("Digite o ID do produto: ")
                buscar_produto(id_produto, cursor)

            elif escolha == "2":
                listar_chaves_produtos()

            elif escolha == "3":
                print("Saindo...")
                break

            else: print("Escolha inválida. Por favor, tente novamente.")

    finally:
        cursor.close()
        conn.close()

menu()

# Justificativa
# Precisei utilizar variáveis de ambiente para armazenar a URL de conexão com o banco de dados.