import os

import psycopg
import redis
from dotenv import load_dotenv

load_dotenv()

# O DB padrão é 0, mas podemos usar outro 16 bancos padrões do próprio Redis, o que estou utilizando é o 10.
r = redis.Redis(host="localhost", port=6379, db=10, decode_responses=True)

# Conexão com o banco de dados PostgreSQL por meio de URL, há como fazer por Docker também
DATABASE_URL = os.getenv("DATABASE_URL")

# Tempo de expiração do cache em segundos (TTL - Time To Live). O atual é de 60 segundos, mas pode ser alterado caso necessário.
# Não há um TTL padrão, mas é recomendado que seja definido para evitar que o cache fique desatualizado.
# Ou seja, se não houver um TTL definido, o cache continuará do jeito que estava antes, mas ficará armazenado indefinidamente.
CACHE_TTL = 60

# Função para obter a conexão com o banco de dados
def get_conn():
    return psycopg.connect(DATABASE_URL)

# 1. Buscar produto no Redis (cache) e, caso não exista, buscar no PostgreSQL como fallback e assim salvar no Redis.
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

# 2. Listar as chaves de produtos presentes no Redis
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

# Mostrar o menu de opções
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

# Executar o menu se o script for executado diretamente
if __name__ == "__main__":
    menu()
