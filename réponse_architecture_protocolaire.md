Partie « Commandes supportées »

|   Commande   |   Syntaxe exacte   |   Effet attendu                      |   Réponse du serveur            |   Responsable côté serveur**         |
| ------------ | ------------------ | ------------------------------------ | ------------------------------- | ------------------------------------ |
| `/nick`      | `/nick <pseudo>`   | Attribue un pseudo unique            | Message de bienvenue ou erreur  | `set_pseudo()`                       |
| `/join`      | `/join <canal>`    | Rejoindre ou créer un canal          | Confirmation de canal rejoint   | `rejoindre_canal()`                  |
| `/msg`       | `/msg <texte>`     | Envoyer un message dans le canal     | Diffusé aux membres du canal    | `envoyer_message()`                  |
| `/read`      | `/read`            | Rappel que tout est en direct        | Message explicatif              | `lire_messages()`                    |
| `/log`       | `/log`             | Voir les 10 dernières entrées du log | 10 lignes de log                | `lire_logs()`                        |
| `/alert`     | `/alert <texte>`   | Envoyer une alerte à tous            | Message d'alerte + confirmation | `envoyer_alerte()`                   |
| `/quit`      | `/quit`            | Déconnexion propre                   | Message d’au revoir             | `handle()`                           |

Partie « Structure interne – Qui fait quoi ? »

| Élément                      | Rôle dans l’architecture                                            |
| ---------------------------- | ------------------------------------------------------------------- |
| `IRCHandler.handle()`        | Lit les lignes envoyées par le client, appelle les bonnes fonctions |
| `etat_serveur`               | Contient les infos sur les utilisateurs, canaux, sujets, etc.       |
| `log()`                      | Enregistre les actions dans le fichier `serveur.log`                |
| `broadcast_system_message()` | Envoie un message à tous les clients connectés                      |

Partie « Points de défaillance potentiels »

|   Zone fragile                 |   Cause possible                      |  *Conséquence attendue                  |   Présence de gestion d’erreur ?        |
| ------------------------------ | ------------------------------------- | --------------------------------------- | --------------------------------------- |
| `wfile.write(...)`             | Socket cassée                         | Message perdu, plantage silencieux      | Oui, `try/except` avec `continue`       |
| Modification d’`etat_serveur`  | Accès concurrent non verrouillé       | Incohérence mémoire                     | Oui, protégé par `threading.Lock()`     |
| Lecture du fichier log         | Fichier manquant ou illisible         | Erreur d’exécution, pas de logs envoyés | Oui, `try/except`                       |
| Pseudo déjà pris (`/nick`)     | Deux clients demandent le même pseudo | Refus d’un des deux                     | Oui, renvoi “pseudo déjà pris”          |
| Utilisateur sans canal courant | `/msg` ou `/topic` sans `/join`       | Commande refusée                        | Oui, message “vous n’avez pas de canal” |
| `split()` dans `/whisper`      | Mauvais format                        | Erreur de découpage                     | Oui, avec message d'erreur              |
