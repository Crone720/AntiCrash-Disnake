import disnake, aiosqlite
from disnake.ext import commands
from disnake import TextInputStyle, AuditLogAction

async def create_tables():
    async with aiosqlite.connect('anticrash.db') as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS anticrash (
                memberid INTEGER PRIMARY KEY,
                editmemberid INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memberid INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)

async def log_attempt(member_id, description):
    async with aiosqlite.connect('anticrash.db') as db:
        await db.execute("INSERT INTO logs (memberid, description) VALUES (?, ?)", (member_id, description))
        await db.commit()

async def addcheck_whitelist(user_id):
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (user_id,))
        result = await cursor.fetchone()
        if result:
            return f"Пользователь <@{user_id}> уже **находится** в белом списке."
        else:
            await db.execute("INSERT INTO anticrash (memberid) VALUES (?)", (user_id,))
            await db.commit()
            return f"Пользователь <@{user_id}> успешно **добавлен** в белом списке."

async def revovecheck_whitelist(user_id):
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (user_id,))
        result = await cursor.fetchone()
        if not result:
            return f"Пользователь <@{user_id}> **не находится** в белом списке."
        else:
            await db.execute("DELETE FROM anticrash WHERE memberid=?", (user_id,))
            await db.commit()
            return f"Пользователь <@{user_id}> успешно **удалён** из белого списка."

async def check_webhook_update(creator):
    if creator.id == creator.guild.owner_id:
        return
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (creator.id,))
        result = await cursor.fetchone()
        if not result:
            await log_attempt(creator.id, "Создание / Удаление Вебхука")
            await creator.ban(reason="Возможная попытка краша")

async def get_channel_creator(guild, created_channel):
    async for entry in guild.audit_logs(action = AuditLogAction.channel_create):
        if entry.target == created_channel:
            return entry.user
    return None

async def get_bot_adder(guild, member):
    async for entry in guild.audit_logs(action = AuditLogAction.bot_add):
        if entry.target == member:
            return entry.user
    return None

async def check_channel_create(channel, member):
    if member.id == member.guild.owner_id:
        return
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (member.id,))
        result = await cursor.fetchone()
        if not result:
            await channel.delete()
            await log_attempt(member.id, "Создание канала")
            await member.ban(reason="Возможная попытка краша")

async def get_channel_deleter(guild, deleted_channel):
    async for entry in guild.audit_logs(action = AuditLogAction.channel_delete):
        if entry.target.id == deleted_channel.id:
            return entry.user
    return None

async def check_channel_delete(member):
    if member.id == member.guild.owner_id:
        return
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (member.id,))
        result = await cursor.fetchone()
        if not result:
            await log_attempt(member.id, "Удаление канала (ов)")
            await member.ban(reason="Возможная попытка краша")

async def check_bot_adder(creator, member):
    if creator.id == creator.guild.owner_id:
        return
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (creator.id,))
        result = await cursor.fetchone()
        if not result:
            await member.kick()
            await log_attempt(creator.id, "Добавление ботов (ов)")
            await creator.ban(reason="Возможная попытка краша")


async def check_role_delete(member):
    if member.id == member.guild.owner_id:
        return
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (member.id,))
        result = await cursor.fetchone()
        if not result:
            await log_attempt(member.id, "Удаление Роли")
            await member.ban(reason="Возможная попытка краша")

async def check_role_create(role, member):
    if member.id == member.guild.owner_id:
        return
    async with aiosqlite.connect('anticrash.db') as db:
        cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (member.id,))
        result = await cursor.fetchone()
        if not result:
            await role.delete()
            await log_attempt(member.id, "Создание роли")
            await member.ban(reason="Возможная попытка краша")

async def get_role_creator(guild, created_role):
    async for entry in guild.audit_logs(action = AuditLogAction.role_create):
        if entry.target == created_role:
            return entry.user
    return None

async def get_role_deleter(guild, deleted_role):
    async for entry in guild.audit_logs(action = AuditLogAction.role_delete):
        if entry.target.id == deleted_role.id:
            return entry.user
    return None

class SelectAutoModeration(disnake.ui.StringSelect):
    def __init__(self, author):
        self.author = author
        options=[
            disnake.SelectOption(
                label="Ban-Words",
                value="banword",
                description="."
            ),
            disnake.SelectOption(
                label="Url",
                value="url",
                description="."
            )
        ]
        super().__init__(min_values=1, max_values=1, placeholder="Выберите тип настройки", options=options)

    async def select_callback(self, select, interaction):
        if interaction.author == self.author:
            embed = disnake.Embed(title="Авто-Модерация")
            async with aiosqlite.connect("anticrash.db") as db:
                cursor = await db.cursor()
                if select.values[0] == 'banword':
                    await cursor.execute("SELECT banwordstatus FROM automoderation")
                    result = await cursor.fetchone()
                    current_status = result[0] if result else 0
                    new_status = 1 if current_status == 0 else 0
                    await cursor.execute("UPDATE automoderation SET banwordstatus = ?", (new_status,))
                    embed.add_field(name="Ban-Words", value=f"Статус успешно изменен на {new_status}")
                elif select.values[0] == 'url':
                    await cursor.execute("SELECT urlstatus FROM automoderation")
                    result = await cursor.fetchone()
                    current_status = result[0] if result else 0
                    new_status = 1 if current_status == 0 else 0
                    await cursor.execute("UPDATE automoderation SET urlstatus = ?", (new_status,))
                    embed.add_field(name="URL", value=f"Статус успешно изменен на {new_status}")
            await db.commit()
            await interaction.send(embed=embed, ephemeral=True)
        else:
            await interaction.send("Вы не имеете доступ к данной интеракции", ephemeral=True)
class BackButton(disnake.ui.Button):
    def __init__(self, author):
        self.author = author
        super().__init__(label="Обратно", row=2)

    async def callback(self, interaction: disnake.MessageInteraction) -> None:
        if interaction.author == self.author:
            embed = disnake.Embed(title="Антикраш", description="Чтобы взаимодействовать с функциями **антикраша** взаимодействуйте с кнопками ниже.")      
            await interaction.response.edit_message(embed=embed, view=AntiCrashFirstButton(self.author))
        else:
            await interaction.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

class RemoveForIDModal(disnake.ui.Modal):
    def __init__(self, author):
        self.author = author
        components = [
            disnake.ui.TextInput(
                label="Введите ID кого хотите удалить",
                placeholder="<3",
                custom_id="id",
                style=TextInputStyle.short,
                max_length=25,
            )
        ]
        super().__init__(
            title=f"Удаление Человека по ID",
            custom_id="id3",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        member = inter.text_values["id"]
        if inter.author == self.author:
            view = disnake.ui.View(timeout=None)
            view.add_item(BackButton(self.author))
            getmember = inter.guild.get_member(int(member))
            if getmember:
                result = await revovecheck_whitelist(getmember.id)
                embed = disnake.Embed(title="Антикраш", description=result)
                await inter.response.edit_message(embed=embed, view=view)
            else:
                await inter.send("Участник не найден. Проверьте есть ли участник на сервере или правильность ID", ephemeral=True)
        else:
            await inter.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

class SearchLogsbyModal(disnake.ui.Modal):
    def __init__(self, author):
        self.author = author
        components = [
            disnake.ui.TextInput(
                label="Введите ID кого хотите просмотреть",
                placeholder="<3",
                custom_id="id",
                style=TextInputStyle.short,
                max_length=25,
            )
        ]
        super().__init__(
            title=f"Просмотр логов по ID",
            custom_id="id3",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        member = inter.text_values["id"]
        if inter.author == self.author:
            view = disnake.ui.View(timeout=None)
            view.add_item(BackButton(self.author))
            async with aiosqlite.connect('anticrash.db') as db:
                cursor = await db.execute("SELECT * FROM logs WHERE memberid=? ORDER BY id DESC LIMIT 10", (member,))
                rows = await cursor.fetchall()
                
                if not rows:
                    await inter.response.send_message("Нет записей о попытках краша от указанного пользователя.", ephemeral=True)
                    return
                
                embed = disnake.Embed(title=f"Последние 10 попыток краша {member}")
                for row in rows:
                    timestamp, description = row[2], row[3]
                    embed.add_field(name=f"{timestamp}", value=description, inline=False)
                
                await inter.response.edit_message(embed=embed)
        else:
            await inter.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

class AddForIDModal(disnake.ui.Modal):
    def __init__(self, author):
        self.author = author
        components = [
            disnake.ui.TextInput(
                label="Введите ID кого хотите добавить",
                placeholder="<3",
                custom_id="id",
                style=TextInputStyle.short,
                max_length=25,
            )
        ]
        super().__init__(
            title=f"Добавления Человека по ID",
            custom_id="id3",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        member = inter.text_values["id"]
        if inter.author == self.author:
            view = disnake.ui.View(timeout=None)
            view.add_item(BackButton(self.author))
            getmember = inter.guild.get_member(int(member))
            if getmember:
                result = await addcheck_whitelist(getmember.id)
                embed = disnake.Embed(title="Антикраш", description=result)
                await inter.response.edit_message(embed=embed, view=view)
            else:
                await inter.send("Участник не найден. Проверьте есть ли участник на сервере или правильность ID", ephemeral=True)
        else:
            await inter.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

class SearchLogsbyButton(disnake.ui.Button):
    def __init__(self, author):
        self.author = author
        super().__init__(label="Искать по ID", row=2)

    async def callback(self, interaction: disnake.MessageInteraction) -> None:
        await interaction.response.send_modal(modal=SearchLogsbyModal(self.author))
    

class AddButtonSendModal(disnake.ui.Button):
    def __init__(self, author):
        self.author = author
        super().__init__(label="Добавить по ID", row=2)

    async def callback(self, interaction: disnake.MessageInteraction) -> None:
        await interaction.response.send_modal(modal=AddForIDModal(self.author))
    
class RemoveButtonSendModal(disnake.ui.Button):
    def __init__(self, author):
        self.author = author
        super().__init__(label="Удалить по ID", row=2)

    async def callback(self, interaction: disnake.MessageInteraction) -> None:
        await interaction.response.send_modal(modal=RemoveForIDModal(self.author))
    

class RemoveWhitelistSelect(disnake.ui.UserSelect):
    def __init__(self, author):
        self.author = author
        super().__init__(placeholder='Укажите Пользователя', min_values=1, max_values=1, row=1)

    async def callback(self, interaction: disnake.MessageInteraction):
        if interaction.author == self.author:
            member = self.values[0]
            result = await revovecheck_whitelist(member.id)
            embed = disnake.Embed(title="Антикраш", description=result)
            view = disnake.ui.View(timeout=None)
            view.add_item(BackButton(self.author))
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

class AddWhitelistSelect(disnake.ui.UserSelect):
    def __init__(self, author):
        self.author = author
        super().__init__(placeholder='Укажите Пользователя', min_values=1, max_values=1, row=1)

    async def callback(self, interaction: disnake.MessageInteraction):
        if interaction.author == self.author:
            member = self.values[0]
            result = await addcheck_whitelist(member.id)
            embed = disnake.Embed(title="Антикраш", description=result)
            view = disnake.ui.View(timeout=None)
            view.add_item(BackButton(self.author))
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

class AntiCrashFirstButton(disnake.ui.View):
    def __init__(self, author):
        self.author = author
        super().__init__(timeout=None)

    @disnake.ui.button(label="Добавить в белый список", custom_id="buttonadduser")
    async def buttonadduser(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author == self.author:
            embed = disnake.Embed(title="Антикраш", description="Чтобы добавить **человека** в белый список укажите его в меню")
            view = disnake.ui.View(timeout=None)
            view.add_item(AddWhitelistSelect(self.author))
            view.add_item(AddButtonSendModal(self.author))
            view.add_item(BackButton(self.author))
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

    @disnake.ui.button(label="Удалить из белого списка", custom_id="buttonremoveuser")
    async def buttonremoveuser(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author == self.author:
            embed = disnake.Embed(title="Антикраш", description="Чтобы Удалить **человека** из белого списка укажите его в меню")
            view = disnake.ui.View(timeout=None)
            view.add_item(RemoveWhitelistSelect(self.author))
            view.add_item(RemoveButtonSendModal(self.author))
            view.add_item(BackButton(self.author))
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

    @disnake.ui.button(label="Последние Логи", custom_id="buttonlastlogs", row=2)
    async def buttonlastlogs(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author == self.author:
            view = disnake.ui.View(timeout=None)
            view.add_item(SearchLogsbyButton(self.author))
            view.add_item(BackButton(self.author))
            async with aiosqlite.connect('anticrash.db') as db:
                cursor = await db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10")
                rows = await cursor.fetchall()
                embed = disnake.Embed(title="Последние 10 попыток краша")
                for row in rows:
                    member_id, timestamp, description = row[1], row[2], row[3]
                    embed.add_field(name=f"{timestamp}", value=description, inline=False)
                    embed.add_field(name="", value=f"Попытка краша от [Пользователя](https://discord.com/users/{member_id})")
                await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.send("Вы не имеете доступ к данной интеракции", ephemeral=True)

class AntiCrash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await create_tables()

    @commands.slash_command(description="Настройка антикраша")
    async def anticrash(self, interaction: disnake.AppCommandInteraction):
        async with aiosqlite.connect('anticrash.db') as db:
            embed = disnake.Embed(title="Антикраш", description="Чтобы взаимодействовать с функциями **антикраша** взаимодействуйте с кнопками ниже.")
            if interaction.author.id == interaction.guild.owner_id:
                await interaction.response.send_message(embed=embed, view=AntiCrashFirstButton(interaction.author))
                return
            cursor = await db.execute("SELECT memberid FROM anticrash WHERE memberid=?", (interaction.author.id,))
            result = await cursor.fetchone()
            if result:
                await interaction.response.send_message(embed=embed, view=AntiCrashFirstButton(interaction.author))
                return
            await interaction.send("куда ручки полезли?", ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        creator = await get_channel_creator(channel.guild, channel)
        await check_channel_create(channel, creator)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        creator = await get_channel_deleter(channel.guild, channel)
        await check_channel_delete(creator)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        creator = await get_role_creator(role.guild, role)
        await check_role_create(creator)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        creator = await get_role_deleter(role.guild, role)
        await check_role_delete(creator)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        guild = channel.guild
        webhook_create, webhook_update, webhook_delete = None, None, None
        async for entry in guild.audit_logs():
            if entry.action == disnake.AuditLogAction.webhook_create and not webhook_create:
                webhook_create = entry
            elif entry.action == disnake.AuditLogAction.webhook_delete and not webhook_delete:
                webhook_delete = entry
            await check_webhook_update(entry.user)
        
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            adder = await get_bot_adder(member.guild, member)
            await check_bot_adder(adder, member)

def setup(bot):
    bot.add_cog(AntiCrash(bot))
# Repository - https://github.com/Crone720/AntiCrash-Disnake
# Developed by ._.tomioka (Discord)