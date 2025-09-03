# Stack Exchange API – Guia 2025: Como Gerar um Access Token OAuth

Este guia mostra como criar uma aplicação no StackApps, configurar OAuth e obter um **Access Token** para fazer requisições autenticadas na API do Stack Exchange.

---

## Passo 1: Registrar sua Aplicação

1. Acesse: [https://stackapps.com/apps](https://stackapps.com/apps) 
2. Login / Registrar 
3. Clique em **“Register an application”**

![Passo 1 – Registrar aplicação](images/1.png)

4. Preencha os campos:
   - **Application name**: `Stack Overflow Miner` (ou outro nome)
   - **Application description**: breve descrição (ex: `Aplicação para minerar dados do Stack Overflow`)
   - **Application URL**: `https://stackexchange.com`
   - **Application icon**: opcional
   - ✅ Marque “I agree to the terms and conditions”

5. Clique em **Register application**

---

![Passo 2: Gerar uma API Key](images/3.png)

1. Clique em **“Generate new API key”**
2. Preencha:
   - **Name**: ex.: `StackOverflowMinerKey`
   - **Expires in**: `90 days`

![Passo 2 – Gerar API Key](images/4.png)

3. Clique em **Generate**

---

## Passo 3: Configurar OAuth

1. Clique em **“Manage OAuth”**

![Passo 3 – Gerenciar OAuth](images/5.png)

2. Marque:
   - ✅ **Confidential client** → **Authorization Code**
   - **OAuth domain**: `stackexchange.com`
   - ⛔️ **Não marque** “Enable Non-Web Client OAuth Redirect URI”

3. Clique em **Save changes**

---

## Passo 4: Criar um Client Secret

1. Clique em **“Generate new client secret”**
2. Nomeie como quiser (ex: `StackOverflowMinerSecret`)
3. Clique em **Add**

![Passo 4 – Criar Client Secret](images/6.png)

4. Salvar o segredo. 
---

## Passo 5: Autorizar Aplicação e Obter o Código

Abra este link no navegador (substitua `YOUR_CLIENT_ID`):

https://stackoverflow.com/oauth?client_id=YOUR_CLIENT_ID&scope=no_expiry&redirect_uri=https://stackexchange.com/oauth/login_success


Faça login, autorize a aplicação, e copie o `code` da URL:
![Passo 7 – Código de autorização](images/7.png)

https://stackexchange.com/oauth/login_success?code=SEU_CODIGO_AQUI

![Passo 7 – Código de autorização](images/8.png)


---

## 📬 Passo 6: Trocar Código pelo Access Token

Execute o seguinte comando no terminal:

```bash
curl -X POST https://stackoverflow.com/oauth/access_token \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret='YOUR_CLIENT_SECRET' \
  -d code='SEU_CODIGO' \
  -d redirect_uri=https://stackexchange.com/oauth/login_success
```
Use aspas simples '...' se o valor contiver caracteres como ( ou ).

![Passo 8 – Código de autorização](images/9.png)

Salvar o token. 