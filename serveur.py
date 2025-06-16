from socketserver import ThreadingTCPServer, StreamRequestHandler
import threading
import sys
import json
import os
from datetime import datetime

# Fichier de persistance de l'état
ETAT_FICHIER = "etat_serveur.json"
LOG_FICHIER = "serveur.log"

# État partagé du serveur
etat_serveur = {
    "utilisateurs": {},  # pseudo -> {"canal": str, "wfile": file, "role": str}
    "canaux": {},        # nom_canal -> [pseudo1, pseudo2, ...]
    "lock": threading.Lock(),
}

ROLES_AUTORISES_ALERT = {"admin", "moderator"}

def log(message):
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ligne = f"[{horodatage}] {message}\n"
    with open(LOG_FICHIER, "a") as f:
        f.write(ligne)
    print(ligne, end="")
    broadcast_system_message(f"[ALERTE] {message}")

def broadcast_system_message(texte):
    with etat_serveur["lock"]:
        for pseudo, info in etat_serveur["utilisateurs"].items():
            try:
                wfile = info["wfile"]
                wfile.write(f"{texte}\n".encode())
                wfile.flush()
            except:
                continue

def charger_etat():
    if os.path.exists(ETAT_FICHIER):
        try:
            with open(ETAT_FICHIER, "r") as f:
                data = json.load(f)
                etat_serveur["utilisateurs"] = {}  # Les wfile ne sont pas sérialisables
                etat_serveur["canaux"] = data.get("canaux", {})
                print("État du serveur restauré.")
        except Exception as e:
            print(f"Erreur lors du chargement de l'état : {e}")

def sauvegarder_etat():
    try:
        with open(ETAT_FICHIER, "w") as f:
            json.dump({"canaux": etat_serveur["canaux"]}, f)
            print("État du serveur sauvegardé.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de l'état : {e}")

class IRCHandler(StreamRequestHandler):
    def handle(self):
        pseudo = None
        self.wfile.write(b"Bienvenue sur CanaDuck IRC !\n")

        while True:
            try:
                ligne = self.rfile.readline()
                if not ligne:
                    break
                commande = ligne.decode().strip()
                if not commande:
                    continue

                if commande.startswith("/nick "):
                    pseudo = self.set_pseudo(commande[6:].strip())
                    
                elif commande.startswith("/join "):
                    self.rejoindre_canal(pseudo, commande[6:].strip())
                    
                elif commande.strip() == "/part":   #ajout
                    self.quitter_canal(pseudo)
                    
                elif commande.startswith("/msg "):
                    self.envoyer_message(pseudo, commande[5:].strip())
                    
                elif commande.startswith("/whisper "):  #ajout
                    self.envoyer_prive(pseudo, commande[9:].strip())
                    
                elif commande == "/read":
                    self.lire_messages(pseudo)
                    
                elif commande == "/log":
                    self.lire_logs()
                    
                elif commande.startswith("/alert "):
                    self.envoyer_alerte(pseudo, commande[7:].strip())
                    
                elif commande.strip() in ["/users", "/who"]:    #ajout
                    self.lister_utilisateurs(pseudo)
                    
                elif commande == "/list":
                    self.lister_canaux()
                
                elif commande == "/quit":
                    self.wfile.write(b"Au revoir !\n")
                    break
                else:
                    self.wfile.write(b"Commande inconnue.\n")

            except Exception as e:
                self.wfile.write(f"Erreur : {e}\n".encode())
                break

        # Nettoyage à la déconnexion
        if pseudo:
            with etat_serveur["lock"]:
                if pseudo in etat_serveur["utilisateurs"]:
                    canal = etat_serveur["utilisateurs"][pseudo].get("canal")
                    if canal and pseudo in etat_serveur["canaux"].get(canal, []):
                        etat_serveur["canaux"][canal].remove(pseudo)
                    del etat_serveur["utilisateurs"][pseudo]
            log(f"{pseudo} s'est déconnecté.")

    def set_pseudo(self, pseudo):
        with etat_serveur["lock"]:
            if pseudo in etat_serveur["utilisateurs"]:
                self.wfile.write("Pseudo déjà pris.\n")
                return None
            # rôle par défaut : user
            etat_serveur["utilisateurs"][pseudo] = {"canal": None, "wfile": self.wfile, "role": "user"}
        self.wfile.write(f"Bienvenue, {pseudo} !\n".encode())
        log(f"{pseudo} s'est connecté.")
        return pseudo
    
    def lister_utilisateurs(self, pseudo):  #ajout
        if not pseudo:
            self.wfile.write(b"Veuillez choisir un pseudo avec /nick.\n")
            return
            
        with etat_serveur["lock"]:
            canal = etat_serveur["utilisateurs"][pseudo].get("canal")
            if not canal:
                self.wfile.write(b"Vous n'etes dans aucun canal. Utilisez /join <canal>.\n")
                return

            utilisateurs_canal = etat_serveur["canaux"].get(canal, [])
            reponse = f"Utilisateurs dans {canal}:\n"
            for user in utilisateurs_canal:
                reponse += f"- {user}\n"
            self.wfile.write(reponse.encode())
            
    def lister_canaux(self):    #ajout
        with etat_serveur["lock"]:
            # On ne liste que les canaux avec au moins un utilisateur
            canaux_actifs = [canal for canal, utilisateurs in etat_serveur["canaux"].items() if utilisateurs]
            if not canaux_actifs:
                self.wfile.write(b"Aucun canal actif pour le moment.\n")
                return

            reponse = "Canaux actifs :\n"
            for canal in canaux_actifs:
                nb_users = len(etat_serveur["canaux"][canal])
                reponse += f"- {canal} ({nb_users} utilisateur(s))\n"
            self.wfile.write(reponse.encode())
            

    def rejoindre_canal(self, pseudo, canal):
        if not pseudo:
            self.wfile.write(b"Veuillez choisir un pseudo avec /nick.\n")
            return
        with etat_serveur["lock"]:
            etat_serveur["utilisateurs"][pseudo]["canal"] = canal
            etat_serveur["canaux"].setdefault(canal, []).append(pseudo)
        self.wfile.write(f"Canal {canal} rejoint.\n".encode())
        log(f"{pseudo} a rejoint le canal {canal}.")

    def envoyer_message(self, pseudo, texte):
        if not pseudo:
            self.wfile.write(b"Veuillez choisir un pseudo avec /nick.\n")
            return
        with etat_serveur["lock"]:
            canal = etat_serveur["utilisateurs"][pseudo].get("canal")
            if not canal:
                self.wfile.write(b"Vous n'avez pas rejoint de canal.\n")
                return
            log(f"Message de {pseudo} sur #{canal} : {texte}")
            for utilisateur in etat_serveur["canaux"].get(canal, []):
                try:
                    wfile = etat_serveur["utilisateurs"][utilisateur]["wfile"]
                    wfile.write(f"[{canal}] {pseudo}: {texte}\n".encode())
                    wfile.flush()
                except:
                    continue

    def lire_messages(self, pseudo):
        self.wfile.write("(Toutes les discussions sont en direct, pas de lecture différée)\n")

    def lire_logs(self):
        try:
            with open(LOG_FICHIER, "r") as f:
                lignes = f.readlines()[-10:]
                for ligne in lignes:
                    self.wfile.write(ligne.encode())
        except Exception as e:
            self.wfile.write(f"Erreur lors de la lecture des logs : {e}\n".encode())
              

    def envoyer_alerte(self, pseudo, texte):
        if not pseudo:
            self.wfile.write(b"Veuillez choisir un pseudo avec /nick.\n")
            return
        role = etat_serveur["utilisateurs"].get(pseudo, {}).get("role", "user")
        if role not in ROLES_AUTORISES_ALERT:
            self.wfile.write(b"Vous n'avez pas les droits pour envoyer une alerte.\n")
            return
        broadcast_system_message(f"[ALERTE MANUELLE] {pseudo}: {texte}")
        log(f"Alerte manuelle de {pseudo} : {texte}")
        self.wfile.write("Alerte envoyée.\n")
        
    def envoyer_prive(self, pseudo, params):    #ajout
        if not pseudo:
            self.wfile.write(b"Veuillez choisir un pseudo avec /nick.\n")
            return
            
        try:
            destinataire, texte = params.split(" ", 1)
        except ValueError:
            self.wfile.write(b"Syntaxe : /whisper <destinataire> <message>\n")
            return

        with etat_serveur["lock"]:
            if destinataire not in etat_serveur["utilisateurs"]:
                self.wfile.write(f"L'utilisateur '{destinataire}' n'existe pas.\n".encode())
                return
            
            try:
                wfile_dest = etat_serveur["utilisateurs"][destinataire]["wfile"]
                wfile_dest.write(f"[Privé de {pseudo}] {texte}\n".encode())
                wfile_dest.flush()
                self.wfile.write(f"Message envoyé à {destinataire}.\n".encode())
            except Exception as e:
                self.wfile.write(f"Impossible d'envoyer le message : {e}\n".encode())
                
    def quitter_canal(self, pseudo):    #ajout
        if not pseudo:
            self.wfile.write(b"Veuillez choisir un pseudo avec /nick.\n")
            return

        with etat_serveur["lock"]:
            canal = etat_serveur["utilisateurs"][pseudo].get("canal")
            if not canal:
                self.wfile.write(b"Vous n'etes dans aucun canal.\n")
                return

            # Retirer l'utilisateur du canal
            if pseudo in etat_serveur["canaux"].get(canal, []):
                etat_serveur["canaux"][canal].remove(pseudo)
            
            # Mettre à jour le statut de l'utilisateur
            etat_serveur["utilisateurs"][pseudo]["canal"] = None

            # Informer les autres membres du canal
            message_depart = f"{pseudo} a quitté le canal {canal}.\n"
            for utilisateur in etat_serveur["canaux"].get(canal, []):
                try:
                    wfile = etat_serveur["utilisateurs"][utilisateur]["wfile"]
                    wfile.write(message_depart.encode())
                    wfile.flush()
                except:
                    continue

        self.wfile.write(f"Vous avez quitté le canal {canal}.\n".encode())
        log(f"{pseudo} a quitté le canal {canal}.")
        

if __name__ == "__main__":
    host, port = "localhost", 63000
    if len(sys.argv) == 2:
        port = int(sys.argv[1])

    charger_etat()

    try:
        with ThreadingTCPServer((host, port), IRCHandler) as server:
            log(f"Serveur CanaDuck IRC actif sur le port {port}")
            server.serve_forever()
    except KeyboardInterrupt:
        log("\nArrêt du serveur...")
    finally:
        sauvegarder_etat()
        
        
    

#commandes /topic et /away demandent + de modifications 
