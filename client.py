import socket
import threading
import sys

def recevoir_messages(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("Déconnecté du serveur.")
                break
            print(data.decode(), end="")
        except:
            print("Erreur lors de la réception.")
            break

def envoyer_messages(sock):
    try:
        while True:
            ligne = input()
            if ligne.strip() == "/quit":
                sock.sendall(b"/quit\n")
                break
            sock.sendall((ligne + "\n").encode())
    except:
        print("Erreur lors de l'envoi.")
    finally:
        sock.close()

if __name__ == "__main__":
    host = input("Adresse du serveur (default: localhost): ").strip() or "localhost"
    port = 63000
    try:
        sock = socket.create_connection((host, port))
        print("Connecté au serveur.")
    except Exception as e:
        print(f"Connexion échouée : {e}")
        sys.exit(1)

    # Démarrage des threads de communication
    threading.Thread(target=recevoir_messages, args=(sock,), daemon=True).start()
    envoyer_messages(sock)

