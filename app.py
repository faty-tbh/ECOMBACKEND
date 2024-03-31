from flask import Flask, render_template, request, redirect, url_for,  flash,request, jsonify
from flask_cors import CORS
from conn import connect_to_snowflake, execute_query
import base64
import os
import traceback
import json
from uuid import uuid4
from confirm_email.email import send_confirmation_email
import pickle




app = Flask(__name__)
app.secret_key = 'faty'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
CORS(app)



@app.route('/')
def home():
    return render_template('acc.html')


@app.route('/submit_article', methods=['POST'])
def submit_details():
    # Retrieve form data
    title = request.form['title']
    author = request.form['author']
    genre = request.form['genre']
    description = request.form['description']
    price = request.form['price']
    quantity = request.form['quantity']
    pd = request.form['pd']
    pages = request.form['pages']
    language = request.form['language']
    image_file = request.files['image']  # Access the uploaded file

    # Print received data to the console
    print("Title:", title)
    print("Author:", author)
    print("Genre:", genre)
    print("Description:", description)
    print("Price:", price)
    print("Quantity:", quantity)
    print("Publication Date:", pd)
    print("Pages:", pages)
    print("Language:", language)

    # Read file data and encode it as a Base64 string
    image_data = image_file.read()
    base64_image = base64.b64encode(image_data).decode('utf-8')

    # Connect to Snowflake
    conn = connect_to_snowflake()

    # Check if the book already exists in the database
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ECOM.PUBLIC.BOOKS WHERE TITLE = %s", (title,))
    count = cursor.fetchone()[0]

    if count == 0:  # Book does not exist, insert new record
        cursor.execute(
            "INSERT INTO ECOM.PUBLIC.BOOKS (TITLE, AUTHOR, GENRE, DESCRIPTION, PRICE, QUANTITY_AVAILABLE, "
            "PUBLICATION_DATE, PAGES, LANGUAGE, IMAGE) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (title, author, genre, description, price, quantity, pd, pages, language, base64_image)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('home'))
    else:
        cursor.close()
        conn.close()
        return jsonify({"message": "Book with the same title already exists."}), 400

@app.route('/search_endpoint', methods=['POST'])
def handle_search():
    data = request.get_json()
    search_query = data.get('query', '')
    app.logger.debug(f"Search Query Received: {search_query}")
    # Ici, vous ferez une recherche réelle dans vos données
    search_results = [{'title': f'Result for {search_query}'}]
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            search_sql = """
                SELECT * FROM ECOM.PUBLIC.BOOKS WHERE TITLE LIKE %s
            """
            like_search_query = f"%{search_query}%"
            cursor.execute(search_sql, (like_search_query,))
            app.logger.debug(f"Executed SQL Query: {search_sql} with search_query: {like_search_query}")

            results = cursor.fetchall()
            app.logger.debug(f"Fetched Results: {results}")

            if results:
                search_results = [{'image' :base64.b64encode(row[1].encode()).decode('utf-8'),'title': row[1], 'author': row[2], 'genre': row[3], 'description': row[4], 'price': row[5], 'quantity' : row[6], 'pd': row[7], 'pages':row[8],'language' : row[9]} for row in results]
            else:
                search_results = [{'message': 'No result found'}]

        app.logger.debug(f"Search Results: {search_results}")

    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        search_results = [{'error': 'An error occurred while searching'}]

    finally:
        conn.close()

    return jsonify(search_results)


from flask import request

@app.route('/update_article', methods=['POST'])
def update_article():
    # Récupérer les données du formulaire
    image_file = request.files['image']
    title = request.form['title']
    author = request.form['author']
    genre = request.form['genre']
    description = request.form['description']
    price = request.form['price']
    quantity = request.form['quantity']
    pd = request.form['pd']
    pages = request.form['pages']
    language = request.form['language']

    # Lire les données du fichier et les encoder en tant que chaîne Base64
    image_data = image_file.read()
    base64_image = base64.b64encode(image_data).decode('utf-8')

    # Connecter à Snowflake
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Exécuter la requête SQL pour mettre à jour les données du livre
            update_sql = """
                UPDATE ECOM.PUBLIC.BOOKS
                SET AUTHOR = %s, GENRE = %s, DESCRIPTION = %s, PRICE = %s, QUANTITY_AVAILABLE = %s,
                    PUBLICATION_DATE = %s, PAGES = %s, LANGUAGE = %s, IMAGE = %s
                WHERE TITLE = %s
            """
            cursor.execute(update_sql, (author, genre, description, price, quantity, pd, pages, language, base64_image, title))
            conn.commit()

            print('Book updated successfully:', title)

    except Exception as e:
        print('An error occurred while updating the book:', e)
        conn.rollback()

    finally:
        conn.close()

    # Rediriger vers une page de confirmation ou une autre page après la mise à jour
    return redirect(url_for('home'))


    

@app.route('/delete_article', methods=['POST'])
def delete_article():
    # Récupérer le titre de l'article à supprimer depuis les données de la requête
    article_title = request.json.get('title')

    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Exécuter la requête SQL pour supprimer l'article basé sur le titre
            delete_sql = """
                DELETE FROM ECOM.PUBLIC.BOOKS
                WHERE TITLE = %s
            """
            cursor.execute(delete_sql, (article_title,))
            conn.commit()

            print('Article deleted successfully:', article_title)
            return redirect(url_for('home'))

    except Exception as e:
        print('An error occurred while deleting the article:', e)
        conn.rollback()

    finally:
        conn.close()

    # Retourner une réponse appropriée
    return 'Article deleted successfully'

@app.route('/get_all_articles', methods=['GET'])
def get_all_articles():
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Sélectionner tous les articles de la base de données
            select_query = """
                SELECT * FROM ECOM.PUBLIC.BOOKS
            """
            cursor.execute(select_query)
            articles = cursor.fetchall()

            # Convertir les résultats en un format adapté pour la réponse JSON
            articles_list = []
            for article in articles:
                article_data = {
                    
                    'title': article[1],
                    'author': article[2],
                    'genre': article[3],
                    'description':article[4],
                    'price': article[5],
                    'quantity': article[6],
                    'publication_date':article[7],
                    'pages' : article[8],
                    'language': article[9],
                    'image': base64.b64encode(article[10].encode()).decode('utf-8'),
                }
                articles_list.append(article_data)

        response = jsonify(articles_list)  # Convertir la liste des articles en JSON
        response.headers.add('Access-Control-Allow-Origin', '*')  # Ajouter l'en-tête CORS
        return response

    except Exception as e:
        # En cas d'erreur, renvoyer un message d'erreur avec un code d'état 500
        return jsonify({'error': f'An error occurred: {e}'}), 500

    finally:
        conn.close()

@app.route('/get_info_panier', methods=['POST'])
def get_info_panier():
    data = request.json  # Récupère les données JSON envoyées depuis l'application React
    title = data.get('title')
    author = data.get('author')
    quantity = data.get('quantity')
    price =data.get('price')
    image= data.get('image')

    # Connecter à Snowflake
    conn = connect_to_snowflake()

    try:
        # Vérifier si le livre existe dans la table book
        with conn.cursor() as cursor:
            cursor.execute("SELECT BOOK_ID FROM ECOM.PUBLIC.BOOKS WHERE TITLE = %s AND AUTHOR = %s", (title, author))
            book_id = cursor.fetchone()

            if book_id:
                # Si le livre existe, insérez son ID et son titre dans la table panier
                cursor.execute("INSERT INTO ECOM.PUBLIC.PANIER (TITLE,PRICE, IMAGE,  QUANTITY) VALUES (%s, %s, %s, %s)", (title,price, image, quantity))
                conn.commit()
                return jsonify({"message": "L'article a été ajouté au panier avec succès."}), 200
            else:
                cursor.execute("INSERT INTO ECOM.PUBLIC.PANIER (TITLE,PRICE, IMAGE,  QUANTITY) VALUES (%s, %s, %s, %s)", (title,price, image, quantity))
                conn.commit()
                return jsonify({"message": "L'article a été ajouté au panier avec succès."}), 200
            


            
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


import base64

@app.route('/cart_items', methods=['GET'])
def get_cart_items():
    # Connect to Snowflake
    conn = connect_to_snowflake()

    try:
        # Select cart items from the PANIER table
        with conn.cursor() as cursor:
            req = """
                SELECT TITLE, PRICE, IMAGE, QUANTITY
                FROM ECOM.PUBLIC.PANIER
            """

            cursor.execute(req)
            articles = cursor.fetchall()

        # Format cart item data
        articles_list = []
        for item in articles:
            article_data = {
                'title': item[0],  # TITLE
                'price': item[1],  # PRICE
                'image':base64.b64encode(item[2].encode()).decode('utf-8'),  # IMAGE
                'quantity': item[3],  # QUANTITY
            }
            articles_list.append(article_data)
            print("here is data :", articles_list)

        return jsonify(articles_list), 200

    except Exception as e:
        # For a production environment, you might want to log the exception details
        # and return a more generic error message to the user.
        print(e)  # Debugging purposes only, you might want to use logging instead
        return jsonify({"error": "An error occurred while processing your request."}), 500

    finally:
        conn.close()

@app.route('/get_books_by_category', methods=['POST'])
def get_books_by_category():
    # Get the category from the JSON payload in the request
    data = request.get_json()
    category = data.get('category')
    print("Category selected:", category)
    
    # Check if the category is provided
    if not category:
        return jsonify({"error": "No category provided."}), 400
    
    # Connect to Snowflake
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT TITLE, AUTHOR, GENRE, DESCRIPTION, PRICE, QUANTITY_AVAILABLE, PUBLICATION_DATE, PAGES, LANGUAGE, IMAGE 
                FROM ECOM.PUBLIC.BOOKS
                WHERE GENRE = %s
            """
            cursor.execute(query, (category,))
            books = cursor.fetchall()

        # Initialize an empty list to hold book dictionaries
        books_list = []

        # Iterate over each book record from the database
        for book in books:
            # Unpack each record into title and image
            title, author, genre, description, price, quantity, date, pages, language, image = book
            
            # Convert the image to a bytes-like object and encode it if it's not None
            if image is not None:
                encoded_image = base64.b64encode(image.encode()).decode('utf-8')
            else:
                encoded_image = None  # Use None or a placeholder for the image

            # Append the book dictionary to the books_list
            books_list.append({'TITLE': title,'AUTHOR': author,'GENRE': genre, 'DESCRIPTION': description, 'PRICE':price, 'QUANTITY_AVAILABLE': quantity, 'PUBLICATION_DATE': date, 'PAGES': pages, 'LANGUAGE': language,  'IMAGE': image})
            
        print('voici', books_list)
        # Return the list of books as JSON
        return jsonify(books_list), 200

    except Exception as e:
        # Log the exception details for debugging
        traceback.print_exc()
        # Return a generic error message to the user
        return jsonify({"error": "An error occurred while processing your request."}), 500

    finally:
        # Ensure the connection is closed
        if conn:
            conn.close()

@app.route('/remove_item', methods=['DELETE'])  # Modifier DELETE en POST
def remove_item():
    # Récupérer le titre de l'article à supprimer depuis les données de la requête
    title = request.json.get('title')

    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Exécuter la requête SQL pour supprimer l'article basé sur le titre
            delete_sql = """
                DELETE FROM ECOM.PUBLIC.PANIER
                WHERE TITLE = %s
            """
            cursor.execute(delete_sql, (title,))
            

            print('Article deleted successfully:', title)
            return jsonify({"message": "L'article a été supprimé avec succès."}), 200

    except Exception as e:
        print('An error occurred while deleting the article:', e)
        conn.rollback()

    finally:
        conn.close()

    # Retourner une réponse appropriée en cas d'échec
    return jsonify({"error": "Une erreur s'est produite lors de la suppression de l'article."}), 500
@app.route('/create_account', methods=['POST'])
def create_account():
    # Récupérer les données envoyées depuis React
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    address = data.get('address')
    telephone = data.get('telephone')
    password = data.get('password')

    # Connexion à Snowflake
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Vérifier si le client existe déjà dans la table customer
            cursor.execute("SELECT COUNT(*) FROM customer WHERE email = %s", (email,))
            count = cursor.fetchone()[0]

            if count == 0:  # Si le client n'existe pas, insérer les données dans la table customer
                cursor.execute(
                    "INSERT INTO customer (name, email, address, telephone, password) VALUES (%s, %s, %s, %s, %s)",
                    (name, email, address, telephone, password)
                )
                conn.commit()
                return jsonify({"message": "Compte créé avec succès."}), 200
            else:
                return jsonify({"message": "Un compte avec cette adresse email existe déjà."}), 400

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    # Récupérer les données envoyées depuis React
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Connexion à Snowflake
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Vérifier si l'utilisateur existe dans la table customer
            cursor.execute("SELECT * FROM customer WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()

            if user:  # Si l'utilisateur existe, retourner ses données
                user_data = {
                    "name": user[1],
                    "email": user[2],
                    "address": user[3],
                    "telephone": user[4]
                }
                return jsonify(user_data), 200
            else:
                return jsonify({"message": "User does not exist."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/get_customer_info', methods=['POST'])
def get_customer_info():
    # Récupérer l'email envoyé depuis React
    data = request.get_json()
    email = data.get('email')

    # Connexion à Snowflake
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Rechercher le client dans la table CUSTOMER basé sur l'email
            cursor.execute("SELECT * FROM CUSTOMER WHERE email = %s", (email,))
            customer = cursor.fetchone()

            if customer:  # Si le client est trouvé, retourner ses informations
                customer_info = {
                    "name": customer[1],
                    "address": customer[2],
                    "telephone": customer[3]
                }
                return jsonify(customer_info), 200
            else:
                return jsonify({"message": "Customer not found."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/edit_user', methods=['POST'])
def update_customer():
    # Récupérer les données du formulaire
    data = request.get_json()
    name= data.get("name")
    email= data.get("email")
    address= data.get("adresse")
    telephone= data.get("telephone")
    password= data.get("password")
    print("h", name)

    
    

    # Connexion à Snowflake
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Exécuter la requête SQL pour mettre à jour les données du client
            update_sql = """
                UPDATE CUSTOMER
                SET name = %s, address = %s, telephone = %s, password = %s
                WHERE email = %s
            """
            cursor.execute(update_sql, (name, address, telephone, password, email))
            conn.commit()

            print('Customer updated successfully:', email)

    except Exception as e:
        print('An error occurred while updating the customer:', e)
        conn.rollback()

    finally:
        conn.close()

    # Rediriger vers une page de confirmation ou une autre page après la mise à jour
    return redirect(url_for('home'))        

from snowflake.connector import ProgrammingError
import uuid
import datetime
@app.route('/process_payment', methods=['POST'])
def submit_payment():
    data = request.get_json()  # Récupérer les données JSON envoyées depuis l'application React

    # Extraire les données du paiement
    email = data.get('email')
    cardholderName = data.get('cardholderName')
    cardNumber = data.get('cardNumber')
    total = data.get('totalPrice')
    order_number = str(uuid.uuid4())  # Générer un identifiant unique pour la commande
    current_date = datetime.date.today()
    status = "In Process"
    items_with_quantities = data.get('items')
    items_with_quantities_str = json.dumps(items_with_quantities)
    adresse= data.get("fullAddress")
    print(adresse)
    print(items_with_quantities_str)
    # quantity = data.get('quantity')
    # titles = data.get('titles')
    # titles_str = ', '.join(titles)
    # quantity_str = ', '.join(quantity)
    # print(titles_str)
    # print(quantity_str)
    

    # Connexion à Snowflake
    conn = connect_to_snowflake()
    

    try:
     with conn.cursor() as cursor:
        for item in items_with_quantities:
              # Première valeur dans chaque sous-liste est le titre
            quantity = item[1]
            title = item[0]

            # Mettre à jour la quantité disponible dans la table des livres
            cursor.execute(
                "UPDATE ECOM.PUBLIC.BOOKS SET QUANTITY_AVAILABLE = QUANTITY_AVAILABLE - %s WHERE TITLE = %s",
                (quantity, title)
            )
            
            # Insérer les données dans la table ORDERS
            cursor.execute(
                "INSERT INTO ORDERS (order_id, email, cardholder, card_number, itemquan, total_price, adress, date_or, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (order_number, email, cardholderName, cardNumber, items_with_quantities_str, total, adresse, current_date, status)
            )
            conn.commit()
            send_confirmation_email(email,cardholderName,order_number,items_with_quantities_str, total, adresse)

            return jsonify({"message": "Paiement effectué avec succès !"}), 200
    except ProgrammingError as e:
        traceback.print_exc()  # Afficher les détails de l'erreur dans la console
        return jsonify({"error": "Une erreur s'est produite lors du traitement de votre paiement."}), 500
    finally:
        conn.close()


@app.route('/get_orders', methods=['GET'])
def get_orders():
    conn = connect_to_snowflake()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM ECOM.PUBLIC.ORDERS"
            cursor.execute(sql)
            # Fetch the result of the query
            orders = cursor.fetchall()
            # Convert query result to list of dicts
            columns = [col[0] for col in cursor.description]
            orders = [dict(zip(columns, row)) for row in orders]
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
    return jsonify(orders)


@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    # Analyse des données JSON envoyées depuis la requête
    data = request.json
    order_id = data.get('orderId')
    new_status = data.get('newStatus')
    print(new_status, order_id)

    # Mettre à jour le statut de la commande dans la base de données
    conn = connect_to_snowflake()
    try:
        with conn.cursor() as cursor:
            # Exécuter la requête SQL pour mettre à jour le statut de la commande
            update_sql = """
                UPDATE ECOM.PUBLIC.ORDERS
                SET status = %s
                WHERE order_id = %s
            """
            cursor.execute(update_sql, (new_status, order_id))
            conn.commit()

            print('Order status updated successfully:', order_id)
    except Exception as e:
        print('An error occurred while updating the order status:', e)
        conn.rollback()
    finally:
        conn.close()

    # Réponse à renvoyer à la page HTML
    response = {'status': 'success', 'message': 'Order status updated successfully'}
    return jsonify(response)

@app.route('/tracking', methods=['POST'])
def track_order():
    # Récupérer l'`order_id` de la requête JSON
    data = request.json
    order_id = data.get('order_id')
    print(order_id)
    conn = connect_to_snowflake()
    

    try:
        # Exécuter la requête pour vérifier si l'`order_id` existe dans la table des commandes
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM ECOM.PUBLIC.ORDERS WHERE order_id = %s", (order_id,))
        result = cursor.fetchone()

        if result:  # Si l'`order_id` existe, renvoyer le statut de la commande
            status = result[0]
            return jsonify({"order_id": order_id, "status": status}), 200
        else:  # Si l'`order_id` n'existe pas, renvoyer un message d'erreur
            return jsonify({"error": "Order ID does not exist."}), 404

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "An error occurred while processing your request."}), 500

    finally:
        conn.close()


# @app.route('/receive_recommendations', methods=['POST'])
# def receive_recommendations():
#     top_ten_books_json = request.json  # Recevoir les recommandations au format JSON
#     print("Recommandations reçues :", top_ten_books_json)
    
#     # Convertir les données JSON en objets Python
#     top_ten_books = json.loads(top_ten_books_json)

#     # Créer une liste pour stocker les données organisées
#     organized_books = []

#     # Traiter les recommandations
#     for i, book in enumerate(top_ten_books, 1):
#         organized_books.append({
#             'BookNumber': i,
#             'BookTitle': book['BookTitle'],
#             'BookAuthor': book['BookAuthor'],
#             'ImageURLM': book['ImageURLM'],
#             'BookRating': book['BookRating']
#         })
#         print(f"Book {i}:")
#         print(f"  Title: {book['BookTitle']}")
#         print(f"  Author: {book['BookAuthor']}")
#         print(f"  Image: {book['ImageURLM']}")
#         print(f"  Rating: {book['BookRating']}")
#         print()  # Ajouter une ligne vide entre chaque livre

#     # Vous pouvez également renvoyer les recommandations dans la réponse JSON
#     return jsonify({"message": "Recommandations reçues avec succès", "recommandations": organized_books})
    


@app.route('/receive_recommendations', methods=['POST'])
def receive_recommendations():
    top_ten_books_json = request.json  # Recevoir les recommandations au format JSON
    
    # Vérifier si des recommandations ont été reçues
    if not top_ten_books_json:
        return jsonify({"error": "No recommendations received"}), 400

    # Convertir les données JSON en objets Python
    top_ten_books = json.loads(top_ten_books_json)

    # Connecter à Snowflake
    conn = connect_to_snowflake()
    try:
        with conn.cursor() as cursor:
            # Supprimer les recommandations existantes de la table
            cursor.execute("DELETE FROM recommendations")

            # Insérer les nouvelles recommandations dans la table
            for i, book in enumerate(top_ten_books, 1):
                cursor.execute("""
                    INSERT INTO ECOM.PUBLIC.RECOMMENDATIONS (BookNumber, BookTitle, BookAuthor, ImageURLM, BookRating)
                    VALUES (%s, %s, %s, %s, %s)
                """, (i, book['BookTitle'], book['BookAuthor'], book['ImageURLM'], book['BookRating']))
                
            conn.commit()  # Valider les changements dans la base de données
            return jsonify({"message": "Recommendations stored successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_recommendations', methods=['GET'])
def get_recommendations():
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Sélectionner toutes les recommandations de la table recommendations
            cursor.execute("SELECT * FROM recommendations")
            recommendations = cursor.fetchall()

            # Convertir les résultats en un format adapté pour la réponse JSON
            recommendations_list = []
            for recommendation in recommendations:
                recommendation_data = {
                    'BookNumber': recommendation[0],
                    'BookTitle': recommendation[1],
                    'BookAuthor': recommendation[2],
                    'ImageURLM': recommendation[3],
                    'BookRating': recommendation[4]
                }
                recommendations_list.append(recommendation_data)

        response = jsonify(recommendations_list)  # Convertir la liste des recommandations en JSON
        return response

    except Exception as e:
        # En cas d'erreur, renvoyer un message d'erreur avec un code d'état 500
        return jsonify({'error': f'An error occurred: {e}'}), 500

    finally:
        conn.close()


@app.route('/rate_book', methods=['POST'])
def rate_book():
    data = request.json  # Récupérer les données JSON envoyées depuis le front-end
    rating = data.get('rating')  # Récupérer le rating
    title = data.get('title')  # Récupérer le titre du livre

    # Connexion à Snowflake
    conn = connect_to_snowflake()

    try:
        with conn.cursor() as cursor:
            # Exécuter la requête SQL pour insérer le rating dans la table Ratings
            cursor.execute(
                "INSERT INTO Ratings (book_title, rating) VALUES (%s, %s)",
                (title, rating)  # Assurez-vous de générer un user_id unique
            )
            conn.commit()

        # Répondre avec un message de confirmation
        return jsonify({'message': 'Rating received and stored successfully'})

    except Exception as e:
        # En cas d'erreur, renvoyer un message d'erreur avec un code d'état 500
        return jsonify({'error': f'An error occurred while storing the rating: {e}'}), 500

    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True) 