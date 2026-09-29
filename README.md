# TP CoAP pour l'IoT

Serveur CoAP développé en Python avec la bibliothèque [`aiocoap`](https://aiocoap.readthedocs.io/). Le projet met en œuvre les requêtes CoAP de base, l'observation de ressources et le transfert blockwise.

## Environnement

- Python 3.8 ou version ultérieure ;
- environnement virtuel Python (`venv`) recommandé ;
- bibliothèque `aiocoap` ;
- un terminal pour le serveur et un second terminal pour les commandes clientes.

Installation :

```bash
python -m venv venv
```

Activation sous Windows :

```bat
venv\Scripts\activate
```

Activation sous macOS ou Linux :

```bash
source venv/bin/activate
```

Installation de la dépendance :

```bash
pip install aiocoap==0.4.7
```

## Démarrage

Dans un premier terminal :

```bash
python server.py
```

Le serveur écoute sur `127.0.0.1:5683` en UDP.

Dans un second terminal, les commandes `aiocoap-client` utilisent l'URL suivante :

```text
coap://127.0.0.1/<ressource>
```

## Ressources exposées

| Ressource | Méthodes | Fonction |
| --- | --- | --- |
| `/temp` | GET, PUT, Observe | Température simulée, modifiée automatiquement toutes les 2 secondes |
| `/led` | GET, PUT | État de la LED (`on` ou `off`) |
| `/logs` | GET, POST, DELETE | Journal d'événements en mémoire |
| `/time` | GET | Heure UTC du serveur |
| `/sensors/room1/temperature` | GET | Température fixe : `23.5` |
| `/sensors/room1/humidity` | GET | Humidité fixe : `55` |
| `/sensors/room1/light` | GET | Luminosité fixe : `150` |
| `/biglog` | GET, Block2 | Journal volumineux utilisé pour tester le transfert par blocs |
| `/.well-known/core` | GET | Annuaire des ressources CoAP |

## Module 1 - Requêtes de base

### Lire la température et l'heure

```bash
aiocoap-client -m get coap://127.0.0.1/temp
aiocoap-client -m get coap://127.0.0.1/time
```

Un GET sur `/time` renvoie le code `2.05 Content` et une date au format UTC, par exemple `2026-09-29T07:54:51Z`.

### Modifier la température

```bash
aiocoap-client -m put --payload "19.0" coap://127.0.0.1/temp
```

La réponse est `2.04 Changed`.

### Piloter la LED

```bash
aiocoap-client -m put --payload "on" coap://127.0.0.1/led
aiocoap-client -m put --payload "off" coap://127.0.0.1/led
```

La ressource n'accepte que `on` et `off`. Toute autre valeur, par exemple `peut-etre`, renvoie `4.00 Bad Request`.

### Utiliser le journal

Ajouter deux entrées :

```bash
aiocoap-client -m post --payload "ALERTE temp 35C" coap://127.0.0.1/logs
aiocoap-client -m post --payload "Porte ouverte" coap://127.0.0.1/logs
```

Chaque POST renvoie `2.01 Created` et crée une ressource `/logs/1`, `/logs/2`, etc. La lecture du journal se fait avec :

```bash
aiocoap-client -m get coap://127.0.0.1/logs
```

Vider le journal :

```bash
aiocoap-client -m delete coap://127.0.0.1/logs
```

La réponse est `2.02 Deleted` et une lecture suivante renvoie `(aucun log)`.

### Codes et résultats observés

| Action | Résultat |
| --- | --- |
| GET `/time` | `2.05 Content` |
| PUT `/temp` avec `19.0` | `2.04 Changed` |
| PUT `/led` avec une valeur invalide | `4.00 Bad Request` |
| Accès à une ressource inexistante | `4.04 Not Found` |
| POST `/logs` | `2.01 Created` |
| DELETE `/logs` | `2.02 Deleted` |

## Module 2 - Observation

Le fichier [`observe.py`](observe.py) observe `/temp` pendant une durée donnée :

```bash
python observe.py 10
```

La réponse initiale possède `Observe=0`, puis les notifications sont reçues à chaque modification de la température. Comme la température change toutes les 2 secondes, une observation de 10 secondes reçoit généralement 5 notifications après la réponse initiale.

Deux clients peuvent observer `/temp` en parallèle. Chaque client reçoit les notifications et, pendant la période commune, les valeurs sont identiques.

Le mécanisme Observe réduit fortement le trafic par rapport à un polling. Pour une mesure toutes les 5 secondes pendant une minute :

- polling toutes les secondes : 60 requêtes et 60 réponses, soit 120 messages ;
- observation : 1 GET, 1 réponse et 12 notifications, soit 14 messages ;
- économie observée : environ 88 % du trafic.

Dans une serre connectée, l'observation peut notamment déclencher automatiquement l'aération ou le chauffage lorsque la température sort d'une plage, et l'arrosage lorsque l'humidité du sol est trop faible.

La méthode `updated_state()` déclenche l'envoi des notifications aux clients abonnés. Elle est appelée après une modification de la température dans `background_task()` et `render_put()`.

## Module 3 - Découverte et blockwise

### Découverte des ressources

```bash
aiocoap-client -m get coap://127.0.0.1/.well-known/core
```

L'annuaire liste les ressources du serveur. `/temp` est marquée `;obs`, ce qui signifie qu'elle est observable. L'annuaire comprend notamment :

```text
/temp
/led
/logs
/time
/sensors/room1/temperature
/sensors/room1/humidity
/sensors/room1/light
/biglog
```

### Lire les capteurs

```bash
aiocoap-client -m get coap://127.0.0.1/sensors/room1/temperature
aiocoap-client -m get coap://127.0.0.1/sensors/room1/humidity
aiocoap-client -m get coap://127.0.0.1/sensors/room1/light
```

La température de la salle 1 vaut `23.5` dans cette simulation.

### Transfert blockwise

Le fichier [`blocks.py`](blocks.py) télécharge `/biglog` avec une taille de bloc choisie :

```bash
python blocks.py 256
python blocks.py 32
```

Le payload de `/biglog` mesure 1 784 octets :

- avec des blocs de 256 octets : 7 blocs, soit 6 blocs de 256 et un dernier de 248 octets ;
- avec des blocs de 32 octets : 56 blocs, soit 55 blocs de 32 et un dernier de 24 octets.

Le blockwise est important pour une caméra IoT, car une image peut dépasser largement la taille maximale d'un paquet UDP. Le contenu est découpé en blocs numérotés ; en cas de perte, seul le bloc concerné doit être retransmis.

Le multicast permettrait également d'interroger un groupe de capteurs en une seule requête, sans connaître individuellement leurs adresses, ou d'envoyer une commande commune à plusieurs capteurs.

## Adaptations pour Windows

Le projet comporte quelques adaptations par rapport à l'énoncé initial :

- `aiocoap-client` n'utilise pas l'option `-e` dans cette version : le contenu est envoyé avec `--payload` ;
- le serveur écoute sur `127.0.0.1` plutôt que sur `::`, car l'adresse générique peut provoquer l'erreur `can not be bound to any-address` sous Windows ;
- l'annuaire `/.well-known/core` est ajouté explicitement avec `resource.WKCResource` ;
- Python 3.8 sous Windows peut utiliser une boucle `Proactor` qui bloque après l'arrêt d'un client observateur ; le projet force donc `WindowsSelectorEventLoopPolicy` ;
- les commandes Unix `timeout`, `wc`, `grep` et l'option `--block` ne sont pas utilisées ; elles sont remplacées par `observe.py` et `blocks.py`.

## Arrêt

Dans le terminal du serveur, utiliser :

```text
Ctrl+C
```

Les journaux et les valeurs des ressources sont stockés en mémoire et sont donc réinitialisés au redémarrage du serveur.
