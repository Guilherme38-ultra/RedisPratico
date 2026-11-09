from unittest.mock import MagicMock

import .app.redis_cache as rc


def test_get_conn():
    """Verifica se a conexão utiliza a DATABASE_URL configurada."""
    mock_conn = MagicMock()

    rc.psycopg2.connect = MagicMock(return_value=mock_conn)

    resultado = rc.get_conn()

    rc.psycopg2.connect.assert_called_once_with(rc.DATABASE_URL)
    assert resultado == mock_conn

def test_buscar_produto_cache_hit(monkeypatch, capsys):
    """Verifica se o produto é recuperado diretamente do Redis."""

    redis_mock = MagicMock()
    redis_mock.exists.return_value = True
    redis_mock.hgetall.return_value = {
        "nome": "Mouse",
        "preco": "99.90"
    }

    monkeypatch.setattr(rc, "r", redis_mock)

    cursor_mock = MagicMock()

    rc.buscar_produto(1, cursor_mock)

    redis_mock.exists.assert_called_once_with("produto:1")
    redis_mock.hgetall.assert_called_once_with("produto:1")

    cursor_mock.execute.assert_not_called()

    assert "Produto carregado do cache" in capsys.readouterr().out

def test_buscar_produto_cache_miss(monkeypatch, capsys):
    """Verifica se o produto é buscado no PostgreSQL e salvo no Redis."""

    redis_mock = MagicMock()
    redis_mock.exists.return_value = False

    monkeypatch.setattr(rc, "r", redis_mock)

    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = ("Teclado", 150.00)

    rc.buscar_produto(2, cursor_mock)

    cursor_mock.execute.assert_called_once_with(
        "select nome, preco from produtos WHERE id = %s",
        (2,)
    )

    redis_mock.hset.assert_called_once_with(
        "produto:2",
        mapping={
            "nome": "Teclado",
            "preco": "150.0"
        }
    )

    redis_mock.expire.assert_called_once_with(
        "produto:2",
        rc.CACHE_TTL
    )

    assert "Produto salvo no cache" in capsys.readouterr().out

def test_buscar_produto_nao_encontrado(monkeypatch, capsys):
    """Verifica o comportamento quando o produto não existe."""

    redis_mock = MagicMock()
    redis_mock.exists.return_value = False

    monkeypatch.setattr(rc, "r", redis_mock)

    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = None

    rc.buscar_produto(999, cursor_mock)

    cursor_mock.execute.assert_called_once()
    redis_mock.hset.assert_not_called()
    redis_mock.expire.assert_not_called()

    assert "Produto não encontrado" in capsys.readouterr().out

def test_listar_chaves_produtos(monkeypatch, capsys):
    """Verifica se as chaves e os dados dos produtos são listados."""

    redis_mock = MagicMock()

    redis_mock.scan.return_value = (
        0,
        ["produto:1"]
    )

    redis_mock.hgetall.return_value = {
        "nome": "Monitor",
        "preco": "899.90"
    }

    monkeypatch.setattr(rc, "r", redis_mock)

    rc.listar_chaves_produtos()

    redis_mock.scan.assert_called_once_with(
        cursor=0,
        match="produto:*",
        count=100
    )

    redis_mock.hgetall.assert_called_once_with("produto:1")

    saida = capsys.readouterr().out

    assert "produto:1" in saida
    assert "Monitor" in saida
    assert "899.90" in saida
