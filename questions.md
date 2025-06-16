1. Qui traite les commandes ?
La fonction IRCHandler.handle() lit les lignes envoyées par le client et appelle les fonctions correspondant aux commandes (/nick, /join, etc.).

— Quelle fonction interprète /msg, /join, etc. ?
Chaque commande est reconnue dans handle() et redirigée vers la fonction associée comme envoyer_message pour /msg, ou rejoindre_canal pour /join.

— Qui accède à la mémoire partagée etat_serveur ?
Toutes les méthodes de la classe IRCHandler utilisent etat_serveur pour lire ou modifier l’état des utilisateurs et des canaux, avec un verrou pour éviter les conflits.

2. Où sont stockées les infos ?
Les informations sont stockées dans le dictionnaire etat_serveur.

— Où est enregistré le canal courant d’un utilisateur ?
Le canal est enregistré dans etat_serveur["utilisateurs"][pseudo]["canal"].

— Où sont les flux de sortie (wfile) associés à chaque client ?
Chaque wfile est stocké dans etat_serveur["utilisateurs"][pseudo]["wfile"].

3. Qui peut planter ?
Certaines erreurs peuvent survenir dans l'exécution.

— Que se passe-t-il si un client quitte sans envoyer /quit ?
Même sans /quit, la déconnexion est détectée quand la lecture échoue, et le pseudo est supprimé de la mémoire partagée.

— Qu’arrive-t-il si un write() échoue ? Est-ce détecté ?
Si un write() échoue, l’erreur est capturée avec un try/except, mais elle n’est pas traitée. Le client reste en mémoire.

— Est-ce qu’un canal vide est supprimé ?
Non, un canal vide reste dans etat_serveur["canaux"] même s’il n’a plus d’utilisateurs.




— Quelles fonctions du serveur manipulent à la fois l’état métier, les sockets réseau et le journal ? Pouvez-vous identifier un exemple de fonction violant le principe de séparation des responsabilités ?
Les fonctions comme envoyer_message, rejoindre_canal, et envoyer_alerte manipulent à la fois l’état (etat_serveur), le réseau (wfile.write) et le journal (log()). Cela viole le principe de séparation des responsabilités car elles mélangent plusieurs rôles.

— Si vous supprimez IRCHandler et branchez un autre protocole (HTTP, WebSocket…), combien de fonctions métier devrez-vous réécrire ?
Il faudrait réécrire toutes les fonctions métier car elles sont directement liées au protocole actuel (texte brut en ligne). Il n’y a pas de couche séparée.

— Le protocole est-il une interface explicite du système ou seulement un comportement émergent ? Autrement dit : peut-on découpler les « effets » des commandes de leur format textuel ?
Le protocole est seulement un comportement émergent. Les effets ne sont pas séparés du format des commandes, donc il n’est pas découplé.

— Quelles sont les opérations atomiques ? Peut-on garantir la cohérence du système si une commande échoue à mi-chemin ? (Ex : /msg réussit à moitié : certains reçoivent, d’autres non)
Les opérations ne sont pas vraiment atomiques. Si une commande échoue en cours (comme /msg), certains clients peuvent recevoir le message et d’autres non, ce qui crée une incohérence possible.

— Quels types d’erreurs le protocole peut-il exprimer ? Différencie-t-on une erreur de syntaxe, une interdiction d’accès, un état illégal (ex : pas de canal), une erreur serveur ?
Le protocole ne différencie pas clairement les types d’erreurs. Toutes les erreurs sont renvoyées sous forme de texte simple.

— Pouvez-vous formaliser le protocole actuel (syntaxe, contraintes) sous forme de grammaire normalisée ?
Non, car il n’y a pas de grammaire claire. Les commandes sont des chaînes commençant par / suivies d’un mot-clé et d’arguments. Ce n’est pas assez structuré pour être normalisé facilement.

— Comment un client non humain saurait-il qu’une ligne reçue est un message utilisateur, une info système, une alerte ?
Il ne pourrait pas le savoir facilement, car tout est du texte brut sans balisage. Il n’y a pas de format structuré.

— Ce protocole peut-il être versionné ? Peut-on prévoir une rétrocompatibilité ?
Non, le protocole n’est pas conçu pour être versionné. Il n’y a pas de mécanisme prévu pour cela.

— Quel est le coût (code, test, fiabilité) de rajouter une commande dans ce protocole par rapport à une API REST bien conçue ?
Le coût est élevé car il faut modifier le handler, écrire la logique, et tester tout en ligne. Ce serait plus simple et structuré avec une API REST.

— Quels tests unitaires sont aujourd’hui impossibles à écrire sans simuler une socket TCP ? Pourquoi ? Que faudrait-il isoler ?
Il est impossible de tester les comportements sans sockets car tout dépend de wfile et rfile. Il faudrait isoler la logique métier du réseau.

— Quels comportements sont aujourd’hui implicites et non testés ? (Exemples : la disparition silencieuse d’un canal vide, la déconnexion d’un client fantôme, l’ordre d’arrivée des messages)
Des comportements comme les canaux qui restent vides, les clients déconnectés sans nettoyage complet, ou l’ordre des messages ne sont pas testés ou explicitement gérés.

— Peut-on simuler un client malveillant qui envoie /msg sans /join ? Comment le serveur réagit-il ? Peut-il être amené à un état invalide ?
Oui, c’est possible. Le serveur répond simplement que l’utilisateur n’a pas de canal, mais il ne casse pas. L’état reste cohérent.

— Le système actuel tolère-t-il les pannes partielles ? (Ex : perte de la socket d’un client, écriture impossible dans le journal, canal corrompu)
Non, il ne les gère pas bien. Si une écriture échoue ou si la socket se ferme, l’erreur est ignorée. Il n’y a pas de mécanisme de reprise.

— L’état du serveur est-il réplicable ? Peut-on faire tourner deux instances concurrentes sans conflit ? Pourquoi pas ?
Non, car l’état est uniquement en mémoire et dans un fichier JSON local. Deux instances ne peuvent pas se partager cet état.

— Quelles ressources sont globales et quelles données pourraient être distribuées ? (Ex : la liste des utilisateurs connectés ? les messages d’un canal ?)
Les utilisateurs et canaux sont globaux. En théorie, les messages pourraient être distribués, mais ce n’est pas prévu ici.

— Que faudrait-il pour brancher un système de persistance robuste (base de données ou message queue) à la place du JSON et du wfile ?
Il faudrait remplacer etat_serveur par une base de données, et envoyer les messages via un système comme RabbitMQ ou Kafka au lieu d’écrire directement sur le wfile.

— Le système actuel est-il capable de gérer des charges réseau variables ? Que se passe-t-il si 1 000 clients se connectent, puis envoient 10 messages chacun dans la même seconde ?
Non, le système ne tiendrait pas cette charge. Il y aurait probablement des lenteurs ou des pertes de messages.

— Quelle architecture (cluster, bus, micro-services, brokers, etc.) serait capable d’absorber cette charge avec fiabilité ?
Une architecture avec des microservices, une base de données partagée, et un bus de messages comme Kafka serait plus adaptée.

— Quelles commandes actuelles pourraient être déléguées à un service distinct (externe) ? Pourquoi ?
Des commandes comme /log, /alert, ou /msg pourraient être déléguées pour séparer les responsabilités et alléger le serveur.

— Peut-on identifier une ou plusieurs interfaces métier dans ce système ? Que faudrait-il pour que le serveur devienne une simple “coquille réseau” pilotant des services internes ?
Oui, la logique métier existe mais elle est mélangée au code réseau. Il faudrait l’extraire en fonctions ou modules indépendants.

— Que manque-t-il à ce projet pour le rendre devops-compatible ? (Tests, logs structurés, monitoring, API REST, configuration, conteneurisation…)
Il manque des tests automatisés, un système de logs structurés, une API REST, de la configuration externe, et une possibilité de conteneurisation (ex : Docker).

— À quelles conditions ce serveur peut-il devenir une base pour une architecture micro-services ? (Critères : isolation, communication explicite, synchronisation, persistance, monitoring…)
Il faudrait isoler la logique métier, ajouter des API explicites, utiliser une base de données ou une file de messages pour la persistance, et intégrer un système de monitoring.
