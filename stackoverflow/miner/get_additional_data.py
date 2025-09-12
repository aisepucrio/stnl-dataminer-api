from django.db import IntegrityError, transaction
import requests
import time
import logging
import os
import sys
from django.utils import timezone
from django.db.models import Q
from stackoverflow.models import (
    StackUser, StackBadge, StackCollective, StackUserBadge,
    StackCollectiveUser, StackCollectiveTag, StackTag
)
from stackoverflow.miner.safe_api_call import safe_api_call
from jobs.models import Task

logger = logging.getLogger(__name__)

def log_progress(message: str, level: str = "info", task_obj: Task = None):
    """
    Exibe feedback no terminal e, se um task_obj for fornecido,
    salva o progresso no banco de dados.
    """
    emojis = {
        "info": "ℹ️", "success": "✅", "warning": "🟡", "error": "❌",
        "system": "⚙️", "fetch": "🔎", "save": "💾", "process": "🔄",
        "badge": "🎖️", "collective": "👥"
    }
    
    # Monta a mensagem para o terminal (continua igual)
    terminal_message = f"[StackOverflow] {emojis.get(level, '➡️ ')} {message}"
    print(terminal_message, flush=True)
    
    # A MÁGICA PARA O FRONTEND ACONTECE AQUI:
    if task_obj:
        # Se a função recebeu um objeto de tarefa, ela atualiza
        # o campo 'operation' com a mensagem limpa e salva no banco.
        task_obj.operation = message 
        task_obj.save(update_fields=["operation"])

def check_required_config(task_obj=None) -> None:
    """Verifica se as variáveis de ambiente essenciais estão configuradas."""
    required_env_vars = ["STACK_API_KEY", "STACK_ACCESS_TOKEN"]

    missing = [var for var in required_env_vars if not os.getenv(var)]
    if missing:
        log_progress(f"Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}", "error", task_obj=task_obj)
        raise ValueError("Variáveis de ambiente não configuradas corretamente no arquivo .env")

def fetch_users_badges(user_ids: list, api_key: str, access_token: str, task_obj=None) -> list:
    """
    Fetch all user badges with pagination and exponential backoff from Stack Exchange API

    Args:
        user_ids (list): List of user IDs to fetch badges for
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token

    Returns:
        list: List of user badges
    """
    ids_string = ';'.join(map(str, user_ids))
    base_url = f"https://api.stackexchange.com/2.3/users/{ids_string}/badges"

    all_badges = []
    page = 1
    base_sleep_time = 2
    max_sleep_time = 30

    while True:
        params = {
            'site': 'stackoverflow',
            'key': api_key,
            'access_token': access_token,
            'filter': '!nNPvSNZxzg',
            'page': page,
            'pagesize': 100
        }

        try:
            data = safe_api_call(base_url, params=params)
            if not data:
                    log_progress("No data returned from API.", "warning", task_obj=task_obj)
                    return []
            
            items = data.get("items", [])
            all_badges.extend(items)

            if 'quota_remaining' in data:
                log_progress(f"API quota remaining: {data['quota_remaining']}", "system", task_obj=task_obj)
                if data['quota_remaining'] < 50:
                    log_progress(f"API quota is low: {data['quota_remaining']}", "warning", task_obj=task_obj)
                    break

            if not data.get("has_more"):
                break

            page += 1
            base_sleep_time = 2  # reset if successful
            log_progress(f"Fetching next page of badges ({page})...", "fetch", task_obj=task_obj)
            time.sleep(base_sleep_time)

        except requests.exceptions.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            if status_code == 429:
                log_progress(f"Rate limit hit. Pausing for {base_sleep_time} seconds...", "warning", task_obj=task_obj)
                time.sleep(base_sleep_time)
                base_sleep_time = min(base_sleep_time * 2, max_sleep_time)
                continue
            elif status_code == 400:
                log_progress(f"API Error (Bad Request) while fetching badges: {e}", "error", task_obj=task_obj)
                break
            else:
                log_progress(f"An unexpected error occurred while fetching badges: {e}", "error", task_obj=task_obj)
                break

    if not all_badges:
        log_progress("No badges were found for this batch of users.", "info", task_obj=task_obj)
    return all_badges


def update_badges_data(users: list, api_key: str, access_token: str, task_obj=None) -> bool:
    """
    Update StackBadge and StackUserBadge based on badges fetched for users.
    """
    if not users:
        return False

    user_ids = [user.user_id for user in users]
    # Trocado logger.info por log_progress
    log_progress(f"-> Buscando badges para {len(user_ids)} usuários...", "badge", task_obj=task_obj)

    badge_data = fetch_users_badges(user_ids, api_key, access_token)
    if not badge_data:
        # Trocado logger.warning por log_progress
        log_progress("Nenhum dado de badge retornado pela API para este lote.", "warning", task_obj=task_obj)
        return False

    created_count = 0

    for item in badge_data:
        badge_name = item.get("name")
        badge_rank = item.get("rank")
        badge_type = item.get("badge_type")
        badge_link = item.get("link")
        badge_description = item.get("description")
        user_id = item.get("user", {}).get("user_id")
        badge_id = item.get("badge_id")
        if badge_id is None:
            continue
        try:
            with transaction.atomic():
                badge_obj, _ = StackBadge.objects.get_or_create(
                    badge_id=badge_id,
                    defaults={
                        "name": badge_name,
                        "badge_type": badge_type,
                        "rank": badge_rank,
                        "link": badge_link,
                        "description": badge_description or "",
                    }
                )
                user = next((u for u in users if u.user_id == user_id), None)
                if user:
                    _, created = StackUserBadge.objects.get_or_create(user=user, badge=badge_obj)
                    if created:
                        created_count += 1
        except IntegrityError as e:
            # Trocado logger.error por log_progress
            log_progress(f"Erro ao salvar badge {badge_id} para usuário {user_id}: {e}", "error", task_obj=task_obj)
            continue

    # Trocado logger.info por log_progress
    if created_count > 0:
        log_progress(f"-> {created_count} novas associações de badges salvas.", "save", task_obj=task_obj)
        
    return created_count > 0

def get_users_to_update(task_obj=None):
    """
    Get users that need to be updated based on time_mined field
    
    Returns:
        QuerySet: Users that need updating
    """
    check_required_config()
    current_time = int(timezone.now().timestamp())
    time_for_recheck = 7 * 24 * 60 * 60  # 7 days in seconds
    
    return StackUser.objects.filter(
        Q(time_mined__isnull=True) |  # Never mined
        Q(time_mined__lt=current_time - time_for_recheck)  # Mined longer ago than the set time for recheck
    )


def fetch_collectives_data(slugs: list, api_key: str, access_token: str, task_obj=None) -> list:
    """
    Fetch collective data from Stack Exchange API with pagination and backoff

    Args:
        slugs (list): List of collective slugs to fetch
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token

    Returns:
        list: List of collective data dictionaries
    """
    batch_size = 100
    all_collectives_data = []
    base_sleep_time = 2
    max_sleep_time = 30

    for i in range(0, len(slugs), batch_size):
        batch_slugs = slugs[i:i + batch_size]
        slugs_string = ';'.join(batch_slugs)
        page = 1

        log_progress(f"-> Fetching data for {len(batch_slugs)} collectives (batch {i // batch_size + 1})...", "collective", task_obj=task_obj)
        

        while True:  # Pagination loop
            params = {
                'site': 'stackoverflow',
                'key': api_key,
                'access_token': access_token,
                'filter': '!nNPvSNVLQY',
                'page': page,
                'pagesize': 100
            }

            base_url = f"https://api.stackexchange.com/2.3/collectives/{slugs_string}"

            try:
                data = safe_api_call(base_url, params=params)
                if not data:
                    log_progress("No data returned from API.", "warning", task_obj=task_obj)
                    return []
                
                items = data.get('items', [])

                if items:
                    all_collectives_data.extend(items)
                    log_progress(f"Found {len(items)} collectives on page {page}.", "info", task_obj=task_obj)
                    
                    for c in items:
                        try:
                            collective_obj, _ = StackCollective.objects.get_or_create(
                                slug=c.get("slug"),
                                defaults={
                                    "name": c.get("name"),
                                    "description": c.get("description"),
                                    "link": c.get("link"),
                                    "last_sync": int(timezone.now().timestamp())
                                }
                            )
                        except IntegrityError as e:
                            log_progress(f"Failed to save collective {c.get('slug')}: {e}", "error", task_obj=task_obj)
                            continue



                        #TODO: StackCollectiveTag for all tags in tags field. 
                else:
                    log_progress(f"No collectives found on page {page}.", "warning", task_obj=task_obj)

                if 'quota_remaining' in data:
                    log_progress(f"API quota remaining: {data['quota_remaining']}", "system", task_obj=task_obj)
                    if data['quota_remaining'] < 100:
                        log_progress(f"API quota is low: {data['quota_remaining']}", "warning", task_obj=task_obj)
                        return all_collectives_data

                if not data.get("has_more"):
                    break

                page += 1
                base_sleep_time = 2  # reset on success
                time.sleep(base_sleep_time)

            except requests.exceptions.RequestException as e:
                status_code = getattr(e.response, 'status_code', None)
                if status_code == 429:
                    log_progress(f"Rate limit hit. Pausing for {base_sleep_time} seconds...", "warning", task_obj=task_obj)
                    time.sleep(base_sleep_time)
                    base_sleep_time = min(base_sleep_time * 2, max_sleep_time)
                    continue
                elif status_code == 400:
                    log_progress(f"API Error (Bad Request) while fetching collectives: {e}", "error", task_obj=task_obj)
                    break
                else:
                    log_progress(f"An unexpected error occurred while fetching collectives: {e}", "error", task_obj=task_obj)
                    break

    return all_collectives_data

def link_users_to_collectives(users: list, fallback_collectives_data: list = None, task_obj=None):
    """
    For each user in the list, create StackCollectiveUser links
    based on their current user.collectives field.

    If a collective slug is not found in the DB, it will be created using the
    fallback_collectives_data (as returned from fetch_collectives_data).
    """
    from stackoverflow.models import StackCollective, StackCollectiveUser

    # Convert fallback_collectives_data (list) to dict {slug: collective_dict}
    if fallback_collectives_data and isinstance(fallback_collectives_data, list):
        fallback_collectives_data = {
            c["slug"]: c for c in fallback_collectives_data if "slug" in c
        }

    link_triples = []  # (user, slug, role)
    slugs = set()

    # Extract (user, slug, role) triples
    for user in users:
        for col in user.collectives or []:
            collective_obj = col.get("collective", {})
            slug = collective_obj.get("slug")
            role = col.get("role")
            if slug:
                link_triples.append((user, slug, role))
                slugs.add(slug)

    if not link_triples:
        return

    # Fetch all relevant collectives from DB
    slug_to_collective = {
        c.slug: c for c in StackCollective.objects.filter(slug__in=slugs)
    }

    created_count = 0
    for user, slug, role in link_triples:
        collective = slug_to_collective.get(slug)

       # If not found, try to create from fallback data
        if not collective and fallback_collectives_data:
            fallback = fallback_collectives_data.get(slug)
            if fallback:
                try:
                    collective, _ = StackCollective.objects.get_or_create(
                        slug=slug,
                        defaults={
                            "name": fallback.get("name"),
                            "description": fallback.get("description", ""),
                            "link": fallback.get("link") or "",
                            "last_sync": int(timezone.now().timestamp())
                        }
                    )
                    slug_to_collective[slug] = collective  # Cache it
                    log_progress(f"Created missing collective: {slug}", "save", task_obj=task_obj)
                except IntegrityError as e:
                    log_progress(f"Failed to create collective {slug}: {e}", "error", task_obj=task_obj)
            else:
                log_progress(f"Data for collective '{slug}' not found to create it.", "warning", task_obj=task_obj)

        if not collective:
            log_progress(f"Could not link user {user.user_id} to missing collective '{slug}'.", "warning", task_obj=task_obj)
            continue

        try:
            with transaction.atomic():
                obj, created = StackCollectiveUser.objects.get_or_create(
                    user=user,
                    collective=collective,
                    defaults={"role": role or "unknown"}
                )
                # If it already exists, update role if it's changed
                if not created and obj.role != (role or "unknown"):
                    obj.role = role or "unknown"
                    obj.save(update_fields=["role"])
                if created:
                    created_count += 1
        except IntegrityError as e:
            log_progress(f"Failed to link user {user.user_id} to collective {collective.slug}: {e}", "error", task_obj=task_obj)


    log_progress(f"-> Created {created_count} new user-collective links.", "save", task_obj=task_obj)

def sync_collective_tags(collectives_data: list, task_obj=None):
    from stackoverflow.models import StackTag, StackCollective, StackCollectiveTag

    if not collectives_data:
        # Trocado logger.warning por log_progress
        log_progress("No collective data provided to sync tags.", "warning", task_obj=task_obj)
        return

    tag_names = set()
    slug_to_tags = {}

    for col in collectives_data:
        slug = col.get("slug")
        tags = col.get("tags", [])
        if not slug or not tags:
            continue
        slug_to_tags[slug] = tags
        tag_names.update(tags)

    tag_objs = {
        tag.name: tag for tag in StackTag.objects.filter(name__in=tag_names)
    }
    existing_tag_names = set(tag_objs.keys())
    missing_tags = tag_names - existing_tag_names
    for tag_name in missing_tags:
        tag_obj = StackTag.objects.create(name=tag_name)
        tag_objs[tag_name] = tag_obj
        # Trocado logger.info por log_progress
        log_progress(f"Created missing Tag: {tag_name}", "save", task_obj=task_obj)

    collectives = {
        c.slug: c for c in StackCollective.objects.filter(slug__in=slug_to_tags.keys())
    }

    created_count = 0
    for slug, tag_list in slug_to_tags.items():
        collective = collectives.get(slug)
        if not collective:
            # Trocado logger.warning por log_progress
            log_progress(f"Collective '{slug}' not found in DB. Skipping tag link.", "warning", task_obj=task_obj)
            continue

        for tag_name in tag_list:
            tag = tag_objs.get(tag_name)
            if not tag:
                # Trocado logger.warning por log_progress
                log_progress(f"Tag '{tag_name}' not found. Skipping link.", "warning", task_obj=task_obj)
                continue

            try:
                with transaction.atomic():
                    _, created = StackCollectiveTag.objects.get_or_create(
                        collective=collective,
                        tag=tag
                    )
                    if created:
                        created_count += 1
            except IntegrityError as e:
                # Trocado logger.error por log_progress
                log_progress(f"Failed to link tag '{tag}' to collective '{collective.slug}': {e}", "error", task_obj=task_obj)

    # Trocado logger.info por log_progress
    if created_count > 0:
        log_progress(f"-> Created {created_count} new links between collectives and tags.", "save", task_obj=task_obj)

def fetch_users_data(user_ids: list, api_key: str, access_token: str, task_obj=None) -> list:
    """
    Fetch complete user data from Stack Exchange API with user-friendly feedback.
    """
    batch_size = 100
    all_users_data = []
    
    for i in range(0, len(user_ids), batch_size):
        batch_ids = user_ids[i:i + batch_size]
        ids_string = ';'.join(map(str, batch_ids))
        page = 1

        # A chamada principal já informa o que está buscando, então os logs aqui foram removidos.
        
        while True:
            params = {
                'site': 'stackoverflow',
                'key': api_key,
                'access_token': access_token,
                'filter': '!T3Audpe81eZTLAf2z2',
                'page': page,
                'pagesize': 100
            }
            base_url = f"https://api.stackexchange.com/2.3/users/{ids_string}"

            try:
                data = safe_api_call(base_url, params=params)
                if not data:
                    log_progress("No user data returned from API for this batch.", "warning", task_obj=task_obj)
                    return []
                
                items = data.get('items', [])
                if items:
                    all_users_data.extend(items)
                
                if 'quota_remaining' in data and data['quota_remaining'] < 100:
                    log_progress(f"API quota is low: {data['quota_remaining']}", "warning", task_obj=task_obj)

                if not data.get("has_more"):
                    break

                page += 1
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                status_code = getattr(e.response, 'status_code', None)
                if status_code == 429:
                    log_progress("Rate limit hit. Pausing for a moment...", "warning", task_obj=task_obj)
                    time.sleep(5) # Pausa curta para rate limit
                    continue
                else:
                    log_progress(f"API Error while fetching users: {e}", "error", task_obj=task_obj)
                    break
    
    return all_users_data


def update_users_data(users: list, api_key: str, access_token: str, task_obj=None) -> set:
    """
    Update multiple users' data with complete information from Stack Exchange API
    
    Args:
        users (list): List of StackUser objects to update
        api_key (str): Stack Exchange API key
        access_token (str): Stack Exchange access token
        
    Returns:
        bool: True if any updates were successful, False otherwise
    """
    if not users:
        return False
        
    user_ids = [user.user_id for user in users]
    log_progress(f"-> Buscando perfis completos para {len(user_ids)} usuários...", "fetch", task_obj=task_obj)
    users_data = fetch_users_data(user_ids, api_key, access_token)
    
    if not users_data:
        log_progress("Nenhum dado de perfil retornado pela API para este lote.", "warning", task_obj=task_obj)
        return False
    
    # Create a dictionary for quick lookup
    users_dict = {user.user_id: user for user in users}
    current_time = int(timezone.now().timestamp())
    updated_count = 0
    skipped_count = 0    
    unique_slugs = set()

    
    for user_data in users_data:
        user_id = user_data.get('user_id')
        if user_id not in users_dict:
            log_progress(f"Usuário ID {user_id} da API não encontrado no lote do banco de dados.", "warning", task_obj=task_obj)
            skipped_count += 1
            continue
            
        user = users_dict[user_id]

           # Collective slugs
        collectives = user_data.get('collectives', [])
        user.collectives = collectives
        for col in collectives:
            slug = col.get("collective", {}).get("slug")
            if slug:
                unique_slugs.add(slug)
        
        # Update user fields
        user.display_name = user_data.get('display_name', user.display_name)
        user.reputation = user_data.get('reputation', user.reputation)
        user.profile_image = user_data.get('profile_image', user.profile_image)
        user.user_type = user_data.get('user_type', user.user_type)
        user.is_employee = user_data.get('is_employee', user.is_employee)
        user.creation_date = user_data.get('creation_date', user.creation_date)
        user.last_access_date = user_data.get('last_access_date', user.last_access_date)
        user.last_modified_date = user_data.get('last_modified_date', user.last_modified_date)
        user.link = user_data.get('link', user.link)
        user.accept_rate = user_data.get('accept_rate', user.accept_rate)
        user.about_me = user_data.get('about_me', user.about_me)
        user.location = user_data.get('location', user.location)
        user.website_url = user_data.get('website_url', user.website_url)
        user.account_id = user_data.get('account_id', user.account_id)
        user.badge_counts = user_data.get('badge_counts', user.badge_counts)
        user.collectives = user_data.get('collectives', user.collectives)
        user.view_count = user_data.get('view_count', user.view_count)
        user.down_vote_count = user_data.get('down_vote_count', user.down_vote_count)
        user.up_vote_count = user_data.get('up_vote_count', user.up_vote_count)
        user.answer_count = user_data.get('answer_count', user.answer_count)
        user.question_count = user_data.get('question_count', user.question_count)
        user.reputation_change_year = user_data.get('reputation_change_year', user.reputation_change_year)
        user.reputation_change_quarter = user_data.get('reputation_change_quarter', user.reputation_change_quarter)
        user.reputation_change_month = user_data.get('reputation_change_month', user.reputation_change_month)
        user.reputation_change_week = user_data.get('reputation_change_week', user.reputation_change_week)
        user.reputation_change_day = user_data.get('reputation_change_day', user.reputation_change_day)
        user.time_mined = current_time
        
        user.save()
        updated_count += 1
    
    log_progress(f"-> {updated_count} perfis de usuários atualizados.", "save", task_obj=task_obj)
    if skipped_count > 0:
        log_progress(f"{skipped_count} usuários foram ignorados (não encontrados no lote).", "warning", task_obj=task_obj)
    return unique_slugs

# Em stackoverflow/functions/data_populator.py

def populate_missing_data(api_key: str, access_token: str, task_obj=None):
    """
    Populate missing data for users that need updating
    """
    # Bloco 1: Verificação Inicial
    users_to_update = list(get_users_to_update())
    total_users = len(users_to_update)
    log_progress(f"Encontrados {total_users} usuários para enriquecer os dados.", "info", task_obj=task_obj)
    
    if total_users == 0:
        return
    
    # Bloco 2: Preparação dos Lotes
    batch_size = 100
    total_batches = (total_users + batch_size - 1) // batch_size
    log_progress(f"O processo será dividido em {total_batches} lotes.", "system", task_obj=task_obj)
    
    # Suas variáveis de controle originais, mantidas
    all_unique_slugs = set()
    total_badges_updated = 0
    processed_user_ids = set()
    
    # Bloco 3: Loop de Processamento
    for i in range(0, total_users, batch_size):
        batch_num = i // batch_size + 1
        batch_users = users_to_update[i:i + batch_size]
        log_progress(f"Processando lote {batch_num}/{total_batches} ({len(batch_users)} usuários)...", "process", task_obj=task_obj)
        
        # Sua lógica original de update, intacta
        batch_slugs = update_users_data(batch_users, api_key, access_token, task_obj=task_obj)
        if batch_slugs:
            all_unique_slugs.update(batch_slugs)
        
        if update_badges_data(batch_users, api_key, access_token, task_obj=task_obj):
            total_badges_updated += 1
            
        processed_user_ids.update([user.user_id for user in batch_users])
    
    # Bloco 4: Processamento de Coletivos
    if all_unique_slugs:
        log_progress(f"Processando {len(all_unique_slugs)} coletivos (Collectives)...", "collective", task_obj=task_obj)
        collectives = fetch_collectives_data(list(all_unique_slugs), api_key, access_token, task_obj=task_obj)
        link_users_to_collectives(users_to_update, collectives, task_obj=task_obj)
        sync_collective_tags(collectives)
    else:
        log_progress("Nenhum coletivo para processar.", "info", task_obj=task_obj)
    
    # Bloco 5: Verificação Final (lógica mantida)
    if len(processed_user_ids) != total_users:
        log_progress(f"Nem todos os usuários foram processados! Esperado: {total_users}, Processado: {len(processed_user_ids)}", "warning", task_obj=task_obj)
    
    # Log de Sucesso Final
    log_progress(f"Enriquecimento finalizado. {len(processed_user_ids)} usuários foram verificados/atualizados.", "success", task_obj=task_obj)
    
def main():
    """
    Main function to populate missing data for all users that need updating.
    """
    from django.conf import settings
    import sys

    try:
        api_key = os.getenv("STACK_API_KEY")
        access_token = os.getenv("STACK_ACCESS_TOKEN")

        if not api_key or not access_token:
            # Trocado logger.error por log_progress
            log_progress("API key or access token not provided in .env file.", "error")
            sys.exit(1)

        # Trocado logger.info por log_progress
        log_progress("Starting data population process...", "system")
        populate_missing_data(api_key, access_token)
        # Trocado logger.info por log_progress
        log_progress("Data population completed successfully.", "success")

    except Exception as e:
        # Trocado logger.error por log_progress
        log_progress(f"An unexpected error occurred during data population: {e}", "error")
        sys.exit(1)
        
if __name__ == "__main__":
    main()

