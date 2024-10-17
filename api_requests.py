from db_config import KEY


def insert_user(cursor, connection, chat_id, username):
    try:
        insert_user_query_pgp = """
            INSERT INTO users (chat_id, username)
            VALUES (%s, pgp_sym_encrypt (%s::text, %s))
            ON CONFLICT (chat_id) DO NOTHING;
            """
        user_data = (
            chat_id,
            username,
            KEY
        )
        cursor.execute(insert_user_query_pgp, user_data)
        connection.commit()
    except Exception as e:
        print("User insert error")
        raise e


def insert_carbon_emission(cursor, connection, chat_id, url, rating, co2):
    try:
        insert_carbon_emission_query_pgp = """
           INSERT INTO carbon_emissions (chat_id, website_url, rating, carbon_emission)
           VALUES (%s, %s, pgp_sym_encrypt(%s::text, %s), pgp_sym_encrypt(%s::text, %s))
           ON CONFLICT (website_url) DO UPDATE SET
               carbon_emission = EXCLUDED.carbon_emission;
           """
        carbon_emission_data = (
            chat_id,
            url,
            rating,
            KEY,
            co2,
            KEY,
        )

        cursor.execute(insert_carbon_emission_query_pgp, carbon_emission_data)
        connection.commit()
    except Exception as e:
        print("Carbon emission insert error")
        raise e


def select_top_websites(cursor, chat_id):
    try:
        select_top_websites_query_pgp = f"""
            SELECT website_url, pgp_sym_decrypt(carbon_emission::bytea, %s) AS carbon_emission
            FROM carbon_emissions
            WHERE chat_id = %s
            ORDER BY carbon_emission DESC
            LIMIT 10;
            """
        cursor.execute(select_top_websites_query_pgp, (KEY, chat_id,))
        response = cursor.fetchall()
        return response
    except Exception as e:
        print("Website select error")
        raise e


def delete_user_history(cursor, connection, chat_id):
    try:
        delete_user_requests_query = """
            DELETE FROM carbon_emissions
            WHERE chat_id = %s
            """
        cursor.execute(delete_user_requests_query, (chat_id,))
        connection.commit()
    except Exception as e:
        print("History delete error")
        raise e
