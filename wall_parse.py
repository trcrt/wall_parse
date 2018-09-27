# https://oauth.vk.com/authorize?client_id=6701596&display=page&response_type=token&v=5.85&revoke=0

import json
import os
import errno
import vk_api
from datetime import datetime

APP_DIR = os.path.dirname(__file__)

CONFIG_FILE_PATH = os.path.join(APP_DIR, 'wall_parse_config.json')
CACHE_FILE_PATH = os.path.join(APP_DIR, 'wall_parse_cache')
PLAIN_OUTPUT_FILE_PATH = os.path.join(APP_DIR, 'output.txt')
HTML_OUTPUT_FILE_PATH = os.path.join(APP_DIR, 'output.html')


class AccessTokensEmpty(Exception):
	pass


def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]


def utime_to_str(utime):
	return datetime.utcfromtimestamp(int(utime)).strftime('%Y-%m-%d %H:%M:%S')


def get_group_posts_count(vk, group_name):
	resp = vk.wall.get(domain=group_name, count=1, offset=0)
	return resp["count"]


def get_liked_or_reposted_posts(vk, all_posts, owner_id, target_user_id):
	zipres = []
	for posts in chunks(all_posts, 25):
		posts = list(posts)
		calls = ['API.likes.isLiked({{"user_id": {0}, "type": "post", "owner_id": {1}, "item_id": {2}}})'
			.format(target_user_id, owner_id, post["wall_post_id"]) for post in posts]
		code = "return [{0}];".format(','.join(calls))
		# print(code)
		resp = vk.execute(code=code)
		zipres += zip(posts, resp)
		# print(resps)
	return [x[0] for x in zipres if (isinstance(x[1], bool) and x[1]) or (not isinstance(x[1], bool) and (x[1]['liked'] + x[1]['copied'] > 0))]


def filter_user_posts(found_posts, target_user_id):
	return [x for x in found_posts if x['user_id'] == target_user_id]


def get_posts(vk, group_name, offset):
	code = '''
		var records = API.wall.get({{"domain": "{0}", "count": 100, "offset": {1}}});
		return [records.count, records.items@.id, records.items@.from_id, records.items@.date, records.items@.text];
	'''.format(group_name, offset)
	resp = vk.execute(code=code)
	count, wall_ids, from_ids, dates, texts = resp
	print("С {0} по {1}".format(
		utime_to_str(dates[-1]),
		utime_to_str(dates[0])))
	found_posts = [{
		'wall_post_id': row[0],
		'user_id': row[1],
		'date': row[2],
		'text': row[3]
	} for row in zip(wall_ids, from_ids, dates, texts)]
	return count, found_posts


def load_config():
	try:
		with open(CONFIG_FILE_PATH) as f:
			config = json.load(f)
	except Exception as e:
		print("Ошибка загрузки конфигурации. Возможно, файл config.json не существует, недоступен или имеет неизвестный формат.")
		raise e
	return config


def get_config_hash(config):
	return config["group_name"] + config["user_name"]


def get_last_parsed_page(config):
	try:
		with open(CACHE_FILE_PATH) as f:
			hashsum, pageindex = [x.strip() for x in f.readlines()]
			if(get_config_hash(config) == hashsum):
				return int(pageindex)
			return 0
	except Exception as e:
		print(e)
		return 0


def save_last_parsed_page(config, page_index):
	try:
		with open(CACHE_FILE_PATH, 'w') as f:
			f.write(get_config_hash(config) + str("\n"))
			f.write(str(page_index))
	except Exception as e:
		pass


def api_wrapper(config, callback):
	tokens = config["access_tokens"]
	access_token = tokens[0]
	vk_session = vk_api.VkApi(token=access_token)
	vk = vk_session.get_api()

	while tokens:
		try:
			return callback(vk)
		except vk_api.ApiError as e:
			print(e)
			tokens.pop()
	raise AccessTokensEmpty()


def save_posts(tag, posts):
	with open(PLAIN_OUTPUT_FILE_PATH, 'a', encoding='utf8') as f:
		for post in posts:
			text = post["text"].replace("\r\n", " ").replace("\n", " ")[:255]
			f.write("{3} {0} {1} {2}\n".format(post["wall_post_id"], post["date"], text, tag))


def write_tag_block_to_html_output(html_file, name, tag, owner_id):
	with open(PLAIN_OUTPUT_FILE_PATH, encoding='utf8') as plain_file:
			html_file.write('<h1>{0}:</h1></br>\n'.format(name))
			for line in plain_file.readlines():
				type, id, date, text = line.split(" ", 3)
				text = text if text.strip() else '///Пост не содержит текста///'
				if type == tag:
					html_file.write("{0}: <a href='https://vk.com/wall{1}_{2}'>{3}</a></br>\n".format(utime_to_str(date), owner_id, id, text))


def save_posts_as_html(config, page, posts_count):
	owner_id = config["owner_id"]
	with open(HTML_OUTPUT_FILE_PATH, 'w', encoding='utf8') as html_file:
		html_file.write('<meta charset="UTF-8">\n')
		html_file.write("Группа: {0}</br>Пользователь: {1}</br> Просмотрено в группе: {2}/{3}</br>\n"
			.format(config["group_name"], config["user_name"], page * 100, posts_count))
		write_tag_block_to_html_output(html_file, "Посты", 'P', owner_id)
		write_tag_block_to_html_output(html_file, "Лайки", 'L', owner_id)


def silentremove(filename):
	try:
		os.remove(filename)
	except OSError as e:
		if e.errno != errno.ENOENT:
			raise


def get_target_user_id(config):
	target_user = api_wrapper(config, lambda vk:
		vk.utils.resolveScreenName(screen_name=config["user_name"]))
	if not target_user:
		print("Пользователь не найден")
		return False
	return target_user["object_id"]


def get_target_group_id(config):
	target_group = api_wrapper(config, lambda vk:
		vk.utils.resolveScreenName(screen_name=config["group_name"]))
	if not target_group:
		print("Группа не найдена")
		return False
	return target_group["object_id"], target_group["type"]


if __name__ == "__main__":
	print("Загрузка конфигурации...")
	config = load_config()
	last_page = get_last_parsed_page(config)
	if last_page == 0:
		silentremove(PLAIN_OUTPUT_FILE_PATH)

	try:
		print("Проверка корректности группы/пользователя...")
		domain = config["group_name"]

		config["owner_id"], config["owner_type"] = get_target_group_id(config) or exit()
		is_group = config["owner_type"] == 'group'
		config["owner_id"] = owner_id = -config["owner_id"] if is_group else config["owner_id"]
		config["target_user_id"] = target_user_id = get_target_user_id(config) or exit()

		posts_count = api_wrapper(config, lambda vk:
			get_group_posts_count(vk, config["group_name"]))
		page = last_page

		print("Начинаем загрузку")
		while page * 100 < posts_count:
			print("Загрузка страницы {0} из ~{1}".format(page, int(posts_count / 100)))
			page += 1
			offset = max(posts_count - page * 100, 0)
			posts_count, all_posts = api_wrapper(config, lambda vk: get_posts(vk, config["group_name"], offset))
			posts = filter_user_posts(all_posts, target_user_id)
			save_posts("P", posts)
			print("Найдено {0} записей на странице.".format(len(posts)))
			if config["need_parse_likes"]:
				print("Ищем лайки...")
				liked_posts = api_wrapper(config, lambda vk: get_liked_or_reposted_posts(vk, all_posts, owner_id, target_user_id))
				print("Найдено {0} лайкнутых записей на странице".format(len(liked_posts)))
				save_posts("L", liked_posts)
			save_last_parsed_page(config, page)
			if page % 10 == 0:
				print("Обновляем html файл вывода")
				save_posts_as_html(config, page, posts_count)
		save_posts_as_html(config, page, posts_count)
		print("Закончено")
	except AccessTokensEmpty as e:
		print("Закончились доступные аккаунты")
		raise e
