import hashlib
from auth import KEY


def get_hash(data):
    return hashlib.sha256(data.encode()).digest()


def is_user_exists(cursor, chat_id):
    try:
        select_user_by_chat_id_query = """
            SELECT EXISTS(
                SELECT 1 FROM users WHERE chat_id_hash = %s
            );
        """
        chat_id_hash = get_hash(str(chat_id))
        cursor.execute(select_user_by_chat_id_query, (chat_id_hash,))
        exists = cursor.fetchone()[0]
        return exists
    except Exception as e:
        print("User checking error")
        raise e


def insert_user(cursor, connection, chat_id, username):
    try:
        select_new_key_query = """
            SELECT gen_random_bytes(16) AS key;
    """
        cursor.execute(select_new_key_query)
        user_key = cursor.fetchone()[0]
        user_key = user_key.hex()
        insert_user_query = """
            INSERT INTO users (chat_id, username, chat_id_hash)
            VALUES (pgp_sym_encrypt(%s::text, %s), pgp_sym_encrypt(%s::text, %s), %s);
        """
        chat_id_hash = get_hash(str(chat_id))
        user_data = (
            chat_id,
            user_key,
            username,
            user_key,
            chat_id_hash
        )
        cursor.execute(insert_user_query, user_data)
        insert_new_user_key_query = """
            INSERT INTO user_keys (chat_id_hash, key) 
            VALUES (%s, pgp_sym_encrypt(%s::text, %s));
        """
        user_key_data = (
            chat_id_hash,
            user_key,
            KEY,
        )
        cursor.execute(insert_new_user_key_query, user_key_data)
        connection.commit()
    except Exception as e:
        print("User  insert error:", e)
        connection.rollback()
        raise e


def insert_carbon_emission(cursor, connection, chat_id, url, rating, co2):
    try:
        select_user_key_query = """
            SELECT pgp_sym_decrypt(key::bytea, %s) FROM user_keys 
            WHERE chat_id_hash = %s;
        """
        chat_id_hash = get_hash(str(chat_id))
        cursor.execute(select_user_key_query, (KEY, chat_id_hash,))
        user_key = cursor.fetchone()[0]
        is_user_request_exists_query = """
            SELECT EXISTS(
                SELECT 1 FROM carbon_emissions 
                WHERE chat_id_hash = %s AND website_url_hash = %s
            );
        """
        website_url_hash = get_hash(url)
        cursor.execute(is_user_request_exists_query, (chat_id_hash, website_url_hash))
        exists = cursor.fetchone()[0]
        if exists:
            update_carbon_emission_query_pgp = """
                UPDATE carbon_emissions
                SET rating = pgp_sym_encrypt(%s::text, %s), carbon_emission = pgp_sym_encrypt(%s::text, %s)
                WHERE chat_id_hash = %s AND website_url_hash = %s;
            """
            updated_carbon_emission_data = (
                rating,
                user_key,
                co2,
                user_key,
                chat_id_hash,
                website_url_hash,
            )
            cursor.execute(update_carbon_emission_query_pgp, updated_carbon_emission_data)
        else:
            insert_carbon_emission_query_pgp = """
                INSERT INTO carbon_emissions (chat_id_hash, website_url, rating, carbon_emission, website_url_hash)
                VALUES (%s, pgp_sym_encrypt(%s::text, %s), pgp_sym_encrypt(%s::text, %s), pgp_sym_encrypt(%s::text, %s), %s);
            """
            new_carbon_emission_data = (
                chat_id_hash,
                url,
                user_key,
                rating,
                user_key,
                co2,
                user_key,
                website_url_hash,
            )
            cursor.execute(insert_carbon_emission_query_pgp, new_carbon_emission_data)

        connection.commit()
    except Exception as e:
        print("Carbon emission insert error")
        connection.rollback()
        raise e


def select_top_websites(cursor, chat_id):
    try:
        select_user_key_query = """
            SELECT pgp_sym_decrypt(key::bytea, %s) FROM user_keys 
            WHERE chat_id_hash = %s;
        """
        chat_id_hash = get_hash(str(chat_id))
        cursor.execute(select_user_key_query, (KEY, chat_id_hash,))
        key = cursor.fetchone()[0]
        select_top_websites_query_pgp = """
            SELECT pgp_sym_decrypt(website_url::bytea, %s), pgp_sym_decrypt(carbon_emission::bytea, %s) AS carbon_emission
            FROM carbon_emissions
            WHERE chat_id_hash = %s
            ORDER BY carbon_emission DESC
            LIMIT 10;
            """
        top_websites_data = (
            key,
            key,
            chat_id_hash,
        )
        cursor.execute(select_top_websites_query_pgp, top_websites_data)
        response = cursor.fetchall()
        return response
    except Exception as e:
        print("Website select error")
        raise e


def delete_user_history(cursor, connection, chat_id):
    try:
        delete_user_requests_query = """
            DELETE FROM carbon_emissions
            WHERE chat_id_hash = %s;
            """
        chat_id_hash = get_hash(str(chat_id))
        cursor.execute(delete_user_requests_query, (chat_id_hash,))
        connection.commit()
    except Exception as e:
        print("History delete error")
        connection.rollback()
        raise e
