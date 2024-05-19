
import sqlite3
from pathlib import Path
from datetime import datetime
from ascii_colors import ASCIIColors, trace_exception
from lollms.types import MSG_TYPE
from lollms.types import BindingType
from lollms.utilities import PackageManager, discussion_path_to_url
from lollms.paths import LollmsPaths
from lollms.databases.skills_database import SkillsLibrary
from lollms.com import LoLLMsCom
from safe_store import TextVectorizer, VisualizationMethod, GenericDataLoader
import json
import shutil
from lollms.tasks import TasksLibrary
__author__ = "parisneo"
__github__ = "https://github.com/ParisNeo/lollms-webui"
__copyright__ = "Copyright 2023, "
__license__ = "Apache 2.0"


# =================================== Database ==================================================================
class DiscussionsDB:
    
    def __init__(self, lollms:LoLLMsCom, lollms_paths:LollmsPaths, discussion_db_name="default"):
        self.lollms = lollms
        self.lollms_paths = lollms_paths
        
        self.discussion_db_name = discussion_db_name
        self.discussion_db_path = self.lollms_paths.personal_discussions_path/discussion_db_name

        self.discussion_db_path.mkdir(exist_ok=True, parents= True)
        self.discussion_db_file_path = self.discussion_db_path/"database.db"

    def create_tables(self):
        db_version = 12
        with sqlite3.connect(self.discussion_db_file_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discussion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    binding TEXT,
                    model TEXT,
                    personality TEXT,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type INT NOT NULL,
                    sender_type INT DEFAULT 0,
                    rank INT NOT NULL DEFAULT 0,
                    parent_message_id INT,
                    created_at TIMESTAMP,
                    started_generating_at TIMESTAMP,
                    finished_generating_at TIMESTAMP,
                    nb_tokens INT,                    
                    discussion_id INTEGER NOT NULL,
                    metadata TEXT,
                    ui TEXT,
                    FOREIGN KEY (discussion_id) REFERENCES discussion(id),
                    FOREIGN KEY (parent_message_id) REFERENCES message(id)
                )
            """)

            cursor.execute("SELECT * FROM schema_version")
            row = cursor.fetchone()

            if row is None:
                cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (db_version,))
            else:
                cursor.execute("UPDATE schema_version SET version = ?", (db_version,))            

            conn.commit()

    def add_missing_columns(self):
        with sqlite3.connect(self.discussion_db_file_path) as conn:
            cursor = conn.cursor()

            table_columns = {
                'discussion': [
                    'id',
                    'title',
                    'created_at'
                ],
                'message': [
                    'id',
                    'binding',
                    'model',
                    'personality',
                    'sender',
                    'content',
                    'message_type',
                    'sender_type',
                    'rank',
                    'parent_message_id',
                    'created_at',
                    'metadata',
                    'ui',
                    'started_generating_at',
                    'finished_generating_at',
                    'nb_tokens',                    
                    'discussion_id'
                ]
            }

            for table, columns in table_columns.items():
                cursor.execute(f"PRAGMA table_info({table})")
                existing_columns = [column[1] for column in cursor.fetchall()]

                for column in columns:
                    if column not in existing_columns:
                        if column == 'id':
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER PRIMARY KEY AUTOINCREMENT")
                        elif column.endswith('_at'):
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TIMESTAMP")
                        elif column=='metadata':
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
                        elif column=='message_type':
                            cursor.execute(f"ALTER TABLE {table} RENAME COLUMN type TO {column}")
                        elif column=='sender_type':
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INT DEFAULT 0")
                        elif column=='parent_message_id':
                            cursor.execute(f"ALTER TABLE {table} RENAME COLUMN parent TO {column}")
                        else:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
                        ASCIIColors.yellow(f"Added column :{column}")
            conn.commit()


    def select(self, query, params=None, fetch_all=True):
        """
        Execute the specified SQL select query on the database,
        with optional parameters.
        Returns the cursor object for further processing.
        """
        with sqlite3.connect(self.discussion_db_file_path) as conn:
            if params is None:
                cursor = conn.execute(query)
            else:
                cursor = conn.execute(query, params)
            if fetch_all:
                return cursor.fetchall()
            else:
                return cursor.fetchone()
            

    def delete(self, query, params=None):
        """
        Execute the specified SQL delete query on the database,
        with optional parameters.
        Returns the cursor object for further processing.
        """
        with sqlite3.connect(self.discussion_db_file_path) as conn:
            cursor = conn.cursor()
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            conn.commit()
   
    def insert(self, query, params=None):
        """
        Execute the specified INSERT SQL query on the database,
        with optional parameters.
        Returns the ID of the newly inserted row.
        """
        
        with sqlite3.connect(self.discussion_db_file_path) as conn:
            cursor = conn.execute(query, params)
            rowid = cursor.lastrowid
            conn.commit()
        self.conn = None
        return rowid

    def update(self, query, params:tuple=None):
        """
        Execute the specified Update SQL query on the database,
        with optional parameters.
        Returns the ID of the newly inserted row.
        """
        
        with sqlite3.connect(self.discussion_db_file_path) as conn:
            conn.execute(query, params)
            conn.commit()
    
    def load_last_discussion(self):
        last_discussion_id = self.select("SELECT id FROM discussion ORDER BY id DESC LIMIT 1", fetch_all=False)
        if last_discussion_id is None:
            last_discussion = self.create_discussion()
            last_discussion_id = last_discussion.discussion_id
        else:
            last_discussion_id = last_discussion_id[0]
        self.current_message_id = self.select("SELECT id FROM message WHERE discussion_id=? ORDER BY id DESC LIMIT 1", (last_discussion_id,), fetch_all=False)
        return Discussion(self.lollms, last_discussion_id, self)
    
    def create_discussion(self, title="untitled"):
        """Creates a new discussion

        Args:
            title (str, optional): The title of the discussion. Defaults to "untitled".

        Returns:
            Discussion: A Discussion instance 
        """
        discussion_id = self.insert(f"INSERT INTO discussion (title) VALUES (?)",(title,))
        return Discussion(self.lollms, discussion_id, self)

    def build_discussion(self, discussion_id=0):
        return Discussion(self.lollms, discussion_id, self)

    def get_discussions(self):
        rows = self.select("SELECT * FROM discussion")         
        return [{"id": row[0], "title": row[1]} for row in rows]

    def does_last_discussion_have_messages(self):
        last_discussion_id = self.select("SELECT id FROM discussion ORDER BY id DESC LIMIT 1", fetch_all=False)
        if last_discussion_id is None:
            last_discussion = self.create_discussion()
            last_discussion_id = last_discussion.discussion_id
        else:
            last_discussion_id = last_discussion_id[0]
        last_message = self.select("SELECT * FROM message WHERE discussion_id=?", (last_discussion_id,), fetch_all=False)
        return last_message is not None
    
    def remove_discussions(self):
        self.delete("DELETE FROM message")
        self.delete("DELETE FROM discussion")


    def export_to_json(self):
        """
        Export all discussions and their messages from the database to a JSON format.

        Returns:
            list: A list of dictionaries representing discussions and their messages.
                Each dictionary contains the discussion ID, title, and a list of messages.
                Each message dictionary contains the sender, content, message type, rank,
                parent message ID, binding, model, personality, created at, and finished
                generating at fields.
        """        
        db_discussions = self.select("SELECT * FROM discussion")
        discussions = []
        for row in db_discussions:
            discussion_id = row[0]
            discussion_title = row[1]
            discussion = {"id": discussion_id, "title":discussion_title, "messages": []}

            rows = self.select(f"SELECT sender, content, message_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens FROM message WHERE discussion_id=?",(discussion_id,))
            for message_row in rows:
                sender = message_row[0]
                content = message_row[1]
                content_type = message_row[2]
                rank = message_row[3]
                parent_message_id = message_row[4]
                binding = message_row[5]
                model = message_row[6]
                personality = message_row[7]
                created_at = message_row[8]
                started_generating_at = message_row[9]
                finished_generating_at = message_row[10]
                nb_tokens =  message_row[11]

                discussion["messages"].append(
                    {"sender": sender, "content": content, "message_type": content_type, "rank": rank, "parent_message_id": parent_message_id, "binding": binding, "model":model, "personality":personality, "created_at":created_at, "started_generating_at":started_generating_at, "finished_generating_at":finished_generating_at, "nb_tokens":nb_tokens}
                )
            discussions.append(discussion)

        return discussions

    def export_all_as_markdown_list_for_vectorization(self):
        """
        Export all discussions and their messages from the database to a Markdown list format.

        Returns:
            list: A list of lists representing discussions and their messages in a Markdown format.
                Each inner list contains the discussion title and a string representing all
                messages in the discussion in a Markdown format.
        """        
        data = self.export_all_discussions_to_json()
        # Initialize an empty result string
        discussions = []
        # Iterate through discussions in the JSON data
        for discussion in data:
            # Extract the title
            title = discussion['title']
            messages = ""
            # Iterate through messages in the discussion
            for message in discussion['messages']:
                sender = message['sender']
                content = message['content']
                # Append the sender and content in a Markdown format
                messages += f'{sender}: {content}\n'
            discussions.append([title, messages])
        return discussions
        
    def export_all_as_markdown(self):
        """
        Export all discussions and their messages from the database to a Markdown format.

        Returns:
            str: A string representing all discussions and their messages in a Markdown format.
                Each discussion is represented as a Markdown heading, and each message is
                represented with the sender and content in a Markdown format.
        """        
        data = self.export_all_discussions_to_json()

        # Initialize an empty result string
        result = ''

        # Iterate through discussions in the JSON data
        for discussion in data:
            # Extract the title
            title = discussion['title']
            # Append the title with '#' as Markdown heading
            result += f'#{title}\n'

            # Iterate through messages in the discussion
            for message in discussion['messages']:
                sender = message['sender']
                content = message['content']
                # Append the sender and content in a Markdown format
                result += f'{sender}: {content}\n'

        return result

    def export_all_discussions_to_json(self):
        # Convert the list of discussion IDs to a tuple
        db_discussions = self.select(
            f"SELECT * FROM discussion"
        )
        discussions = []
        for row in db_discussions:
            discussion_id = row[0]
            discussion_title = row[1]
            discussion = {"id": discussion_id, "title":discussion_title, "messages": []}

            rows = self.select(f"SELECT sender, content, message_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens FROM message WHERE discussion_id=?",(discussion_id,))
            for message_row in rows:
                sender = message_row[0]
                content = message_row[1]
                content_type = message_row[2]
                rank = message_row[3]
                parent_message_id = message_row[4]
                binding = message_row[5]
                model = message_row[6]
                personality = message_row[7]
                created_at = message_row[8]
                started_generating_at = message_row[9]
                finished_generating_at = message_row[10]
                nb_tokens = message_row[11]
                discussion["messages"].append(
                    {"sender": sender, "content": content, "message_type": content_type, "rank": rank, "parent_message_id": parent_message_id, "binding": binding, "model":model, "personality":personality, "created_at":created_at, "started_generating_at":started_generating_at, "finished_generating_at": finished_generating_at,"nb_tokens":nb_tokens}
                )
            discussions.append(discussion)
        return discussions

    def export_discussions_to_json(self, discussions_ids:list):
        # Convert the list of discussion IDs to a tuple
        discussions_ids_tuple = tuple(discussions_ids)
        txt = ','.join(['?'] * len(discussions_ids_tuple))
        db_discussions = self.select(
            f"SELECT * FROM discussion WHERE id IN ({txt})",
            discussions_ids_tuple
        )
        discussions = []
        for row in db_discussions:
            discussion_id = row[0]
            discussion_title = row[1]
            discussion = {"id": discussion_id, "title":discussion_title, "messages": []}
            rows = self.select(f"SELECT sender, content, message_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens FROM message WHERE discussion_id=?",(discussion_id,))
            for message_row in rows:
                sender = message_row[0]
                content = message_row[1]
                content_type = message_row[2]
                rank = message_row[3]
                parent_message_id = message_row[4]
                binding = message_row[5]
                model = message_row[6]
                personality = message_row[7]
                created_at = message_row[8]
                started_generating_at = message_row[9]
                finished_generating_at = message_row[9]
                nb_tokens = message_row[9]
                
                discussion["messages"].append(
                    {"sender": sender, "content": content, "message_type": content_type, "rank": rank, "parent_message_id": parent_message_id, "binding": binding, "model":model, "personality":personality, "created_at":created_at, "started_generating_at":started_generating_at, "finished_generating_at": finished_generating_at, "nb_tokens":nb_tokens}
                )
            discussions.append(discussion)
        return discussions
    
    def import_from_json(self, json_data):
        discussions = []
        data = json_data
        for discussion_data in data:
            discussion_id = discussion_data.id
            discussion_title = discussion_data.title
            messages_data = discussion_data.messages
            discussion = {"id": discussion_id, "title": discussion_title, "messages": []}

            # Insert discussion into the database
            discussion_id = self.insert("INSERT INTO discussion (title) VALUES (?)", (discussion_title,))

            for message_data in messages_data:
                sender = message_data.get("sender")
                content = message_data.get("content")
                content_type = message_data.get("message_type",message_data.get("type"))
                rank = message_data.get("rank")
                parent_message_id = message_data.get("parent_message_id")
                binding = message_data.get("binding","")
                model = message_data.get("model","")
                personality = message_data.get("personality","")
                created_at = message_data.get("created_at",datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                started_generating_at = message_data.get("started_generating_at",datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                finished_generating_at = message_data.get("finished_generating_at",datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                nb_tokens = message_data.get("nb_tokens",datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                discussion["messages"].append(
                    {"sender": sender, "content": content, "message_type": content_type, "rank": rank, "binding": binding, "model": model, "personality": personality, "created_at": created_at, "started_generating_at":started_generating_at, "finished_generating_at": finished_generating_at, "nb_tokens":nb_tokens}
                )

                # Insert message into the database
                self.insert("INSERT INTO message (sender, content, message_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens, discussion_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (sender, content, content_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens, discussion_id))

            discussions.append(discussion)

        return discussions

    def export_discussions_to_markdown(self, discussions_ids:list, title = ""):
        # Convert the list of discussion IDs to a tuple
        discussions_ids_tuple = tuple(discussions_ids)
        txt = ','.join(['?'] * len(discussions_ids_tuple))
        db_discussions = self.select(
            f"SELECT * FROM discussion WHERE id IN ({txt})",
            discussions_ids_tuple
        )
        discussions = f"# {title}" if title!="" else ""
        for row in db_discussions:
            discussion_id = row[0]
            discussion_title = row[1]
            discussions += f"## {discussion_title}\n"

            rows = self.select(f"SELECT sender, content, message_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens FROM message WHERE discussion_id=?",(discussion_id,))
            for message_row in rows:
                sender = message_row[0]
                content = message_row[1]
                content_type = message_row[2]
                rank = message_row[3]
                parent_message_id = message_row[4]
                binding = message_row[5]
                model = message_row[6]
                personality = message_row[7]
                created_at = message_row[8]
                started_generating_at = message_row[9]
                finished_generating_at = message_row[10]
                nb_tokens = message_row[11]

                discussions +=f"### {sender}:\n{content}\n"
            discussions +=f"\n"
        return discussions


class Message:
    def __init__(
                    self,
                    discussion_id,
                    discussions_db,
                    message_type,
                    sender_type,
                    sender,
                    content,
                    metadata                = None,
                    ui                      = None,
                    rank                    = 0,
                    parent_message_id       = 0,
                    binding                 = "",
                    model                   = "",
                    personality             = "",
                    created_at              = None,
                    started_generating_at   = None,
                    finished_generating_at  = None,
                    nb_tokens     = None,
                    id                      = None,
                    insert_into_db          = False
                    ):
        
        self.discussion_id = discussion_id
        self.discussions_db = discussions_db
        self.self = self
        self.sender = sender
        self.sender_type = sender_type
        self.content = content
        self.message_type = message_type
        self.rank = rank
        self.parent_message_id = parent_message_id
        self.binding = binding
        self.model = model
        self.metadata = json.dumps(metadata, indent=4) if metadata is not None and type(metadata)== dict else metadata
        self.ui = ui
        self.personality = personality
        self.created_at = created_at
        self.started_generating_at = started_generating_at
        self.finished_generating_at = finished_generating_at
        self.nb_tokens = nb_tokens

        if insert_into_db:
            self.id = self.discussions_db.insert(
                "INSERT INTO message (sender,  message_type,  sender_type,  sender,  content,  metadata, ui,  rank,  parent_message_id,  binding,  model,  personality,  created_at, started_generating_at,  finished_generating_at, nb_tokens,  discussion_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                (sender, message_type, sender_type, sender, content, metadata, ui, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens, discussion_id)
            )
        else:
            self.id = id


    @staticmethod
    def get_fields():
        return [
            "id",
            "message_type",
            "sender_type",
            "sender",
            "content",
            "metadata",
            "ui",
            "rank",
            "parent_message_id",
            "binding",
            "model",
            "personality",
            "created_at",
            "started_generating_at",
            "finished_generating_at",
            "nb_tokens",
            "discussion_id"
        ]        

    @staticmethod
    def from_db(discussions_db, message_id):
        columns = Message.get_fields()
        rows = discussions_db.select(
            f"SELECT {','.join(columns)} FROM message WHERE id=?", (message_id,)
        )
        data_dict={
            col:rows[0][i]
            for i,col in enumerate(columns)
        }
        data_dict["discussions_db"]=discussions_db
        return Message(
            **data_dict
        )

    @staticmethod
    def from_dict(discussions_db,data_dict):
        data_dict["discussions_db"]=discussions_db
        return Message(
            **data_dict
        )

    def insert_into_db(self):
        self.message_id = self.discussions_db.insert(
            "INSERT INTO message (sender, content, metadata, ui, message_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens, discussion_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            (self.sender, self.content, self.metadata, self.ui, self.message_type, self.rank, self.parent_message_id, self.binding, self.model, self.personality, self.created_at, self.started_generating_at, self.finished_generating_at, self.nb_tokens, self.discussion_id)
        )

    def update_db(self):
        self.message_id = self.discussions_db.insert(
            "INSERT INTO message (sender, content, metadata, ui, message_type, rank, parent_message_id, binding, model, personality, created_at, started_generating_at, finished_generating_at, nb_tokens, discussion_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            (self.sender, self.content, self.metadata, self.ui, self.message_type, self.rank, self.parent_message_id, self.binding, self.model, self.personality, self.created_at, self.started_generating_at, self.finished_generating_at, nb_tokens, self.discussion_id)
        )

    def update(self, new_content, new_metadata=None, new_ui=None, started_generating_at=None, nb_tokens=None, commit=True):
        self.finished_generating_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text = f"UPDATE message SET content = ?"
        params = [new_content]
        if new_metadata is not None:
            text+=", metadata = ?"
            params.append(new_metadata)
        if new_ui is not None:
            text+=", ui = ?"
            params.append(new_ui)

        if started_generating_at is not None:
            text+=", started_generating_at = ?"
            params.append(started_generating_at)

        if nb_tokens is not None:
            text+=", nb_tokens = ?"
            params.append(nb_tokens)


        text +=", finished_generating_at = ? WHERE id = ?"
        params.append(self.finished_generating_at)
        params.append(self.id)
        self.discussions_db.update(
            text, tuple(params)
        )        

    def to_json(self):
        attributes = Message.get_fields()
        msgJson = {}
        for attribute_name in attributes:
            attribute_value = getattr(self, attribute_name, None)
            if attribute_name=="metadata":
                if type(attribute_value) == str:
                    msgJson[attribute_name] = json.loads(attribute_value)
                else:
                    msgJson[attribute_name] = attribute_value
            else:
                msgJson[attribute_name] = attribute_value
        return msgJson

class Discussion:
    def __init__(self, lollms:LoLLMsCom, discussion_id, discussions_db:DiscussionsDB):
        self.lollms = lollms
        self.current_message = None
        self.discussion_id = discussion_id
        self.discussions_db = discussions_db
        self.discussion_folder = self.discussions_db.discussion_db_path/f"{discussion_id}"
        self.discussion_audio_folder = self.discussion_folder / "audio"
        self.discussion_images_folder = self.discussion_folder / "images"
        self.discussion_text_folder = self.discussion_folder / "text_data"
        self.discussion_skills_folder = self.discussion_folder / "skills"
        self.discussion_rag_folder = self.discussion_folder / "rag"
        self.discussion_view_images_folder = self.discussion_folder / "view_images"

        self.discussion_folder.mkdir(exist_ok=True)
        self.discussion_images_folder.mkdir(exist_ok=True)
        self.discussion_text_folder.mkdir(exist_ok=True)
        self.discussion_skills_folder.mkdir(exist_ok=True)
        self.discussion_rag_folder.mkdir(exist_ok=True)
        self.discussion_view_images_folder.mkdir(exist_ok=True)
        self.messages = self.get_messages()
        self.whisper= None
        
        if len(self.messages)>0:
            self.current_message = self.messages[-1]

        # Initialize the file lists
        self.update_file_lists()


        self.vectorizer = TextVectorizer(
            self.lollms.config.data_vectorization_method, # supported "model_embedding" or "tfidf_vectorizer"
            model=self.lollms.model, #needed in case of using model_embedding
            database_path=self.discussion_rag_folder/"db.json",
            save_db=self.lollms.config.data_vectorization_save_db,
            data_visualization_method=VisualizationMethod.PCA,
            database_dict=None)
    
        if len(self.vectorizer.chunks)==0 and len(self.text_files)>0:
            for path in self.text_files:
                data = GenericDataLoader.read_file(path)
                try:
                    self.vectorizer.add_document(path, data, self.lollms.config.data_vectorization_chunk_size, self.lollms.config.data_vectorization_overlap_size, add_first_line_to_all_chunks=True if path.suffix==".csv" else False)
                except Exception as ex:
                    trace_exception(ex)            
            try:
                self.vectorizer.index()
            except Exception as ex:
                trace_exception(ex)            

    def update_file_lists(self):
        self.text_files = [Path(file) for file in self.discussion_text_folder.glob('*')]
        self.image_files = [Path(file) for file in self.discussion_images_folder.glob('*')]
        self.audio_files = [Path(file) for file in self.discussion_audio_folder.glob('*')]
        self.rag_db = [Path(file) for file in self.discussion_rag_folder.glob('*')]


    def remove_file(self, file_name, callback=None):
        try:
            all_files = self.text_files+self.image_files+self.audio_files
            if any(file_name == entry.name for entry in self.text_files):
                fn = [entry for entry in self.text_files if entry.name == file_name][0]
                self.text_files = [entry for entry in self.text_files if entry.name != file_name]
                Path(fn).unlink()
                if len(self.text_files)>0:
                    try:
                        self.vectorizer.remove_document(fn)
                        if callback is not None:
                            callback("File removed successfully",MSG_TYPE.MSG_TYPE_INFO)
                        return True
                    except ValueError as ve:
                        ASCIIColors.error(f"Couldn't remove the file")
                        return False
                else:
                    self.vectorizer = None
            elif any(file_name == entry.name for entry in self.image_files):
                fn = [entry for entry in self.image_files if entry.name == file_name][0]
                self.image_files = [entry for entry in self.image_files if entry.name != file_name]
                Path(fn).unlink()
            elif any(file_name == entry.name for entry in self.audio_files):
                fn = [entry for entry in self.audio_files if entry.name == file_name][0]
                self.audio_files = [entry for entry in self.audio_files if entry.name != file_name]
                Path(fn).unlink()

        except Exception as ex:
            trace_exception(ex)
            ASCIIColors.warning(f"Couldn't remove the file {file_name}")

    def remove_all_files(self):
        # Iterate over each directory and remove all files
        for path in [self.discussion_images_folder, self.discussion_rag_folder, self.discussion_audio_folder, self.discussion_text_folder]:
            for file in path.glob('*'):
                if file.is_file():  # Ensure it's a file, not a directory
                    file.unlink()  # Delete the file
                    
        # Clear the lists to reflect the current state (empty directories)
        self.text_files.clear()
        self.image_files.clear()
        self.audio_files.clear()

    def add_file(self, path, client, tasks_library:TasksLibrary, callback=None, process=True):
        output = ""

        path = Path(path)
        if path.suffix in [".wav",".mp3"]:
            self.audio_files.append(path)
            if process:
                self.lollms.new_message(client.client_id if client is not None else 0, content = "", message_type = MSG_TYPE.MSG_TYPE_FULL)
                self.lollms.info(f"Transcribing ... ")
                if self.whisper is None:
                    if not PackageManager.check_package_installed("whisper"):
                        PackageManager.install_package("openai-whisper")
                        try:
                            import conda.cli
                            conda.cli.main("install", "conda-forge::ffmpeg", "-y")
                        except:
                            ASCIIColors.bright_red("Couldn't install ffmpeg. whisper won't work. Please install it manually")

                    import whisper
                    self.whisper = whisper.load_model("base")
                result = self.whisper.transcribe(str(path))
                transcription_fn = str(path)+".txt"
                with open(transcription_fn, "w", encoding="utf-8") as f:
                    f.write(result["text"])
                tasks_library.info(f"Transcription saved to {transcription_fn}")

        elif path.suffix in [".png",".jpg",".jpeg",".gif",".bmp",".svg",".webp"]:
            self.image_files.append(path)
            if process:
                
                try:
                    view_file = self.discussion_view_images_folder/path.name
                    shutil.copyfile(path, view_file)
                    pth = str(view_file).replace("\\","/").split('/')
                    if "discussion_databases" in pth:
                        pth = discussion_path_to_url(view_file)
                        self.lollms.new_message(client.client_id if client is not None else 0, content = "", message_type = MSG_TYPE.MSG_TYPE_FULL)
                        output = f'<img src="{pth}" width="800">\n\n'
                        self.lollms.full(output, client_id=client.client_id)
                        self.lollms.close_message(client.client_id if client is not None else 0)

                    if self.lollms.model.binding_type not in [BindingType.TEXT_IMAGE, BindingType.TEXT_IMAGE_VIDEO]:
                        # self.ShowBlockingMessage("Understanding image (please wait)")
                        from PIL import Image
                        img = Image.open(str(view_file))
                        # Convert the image to RGB mode
                        img = img.convert("RGB")
                        output += "## image description :\n"+ self.lollms.model.interrogate_blip([img])[0]
                        # output += "## image description :\n"+ self.lollms.model.qna_blip([img],"q:Describe this photo with as much details as possible.\na:")[0]
                        self.lollms.full(output)
                        self.lollms.close_message(client.client_id if client is not None else 0)
                        self.lollms.HideBlockingMessage("Understanding image (please wait)")
                        if self.lollms.config.debug:
                            ASCIIColors.yellow(output)
                    else:
                        # self.ShowBlockingMessage("Importing image (please wait)")
                        self.lollms.HideBlockingMessage("Importing image (please wait)")

                except Exception as ex:
                    trace_exception(ex)
                    self.lollms.HideBlockingMessage("Understanding image (please wait)", False)
                    ASCIIColors.error("Couldn't create new message")
            ASCIIColors.info("Received image file")
            if callback is not None:
                callback("Image file added successfully", MSG_TYPE.MSG_TYPE_INFO)
        else:
            try:
                # self.ShowBlockingMessage("Adding file to vector store.\nPlease stand by")
                self.text_files.append(path)
                ASCIIColors.info("Received text compatible file")
                self.lollms.ShowBlockingMessage("Processing file\nPlease wait ...")
                if process:
                    if self.vectorizer is None:
                        self.vectorizer = TextVectorizer(
                                    self.lollms.config.data_vectorization_method, # supported "model_embedding" or "tfidf_vectorizer"
                                    model=self.lollms.model, #needed in case of using model_embedding
                                    database_path=self.discussion_rag_folder/"db.json",
                                    save_db=self.lollms.config.data_vectorization_save_db,
                                    data_visualization_method=VisualizationMethod.PCA,
                                    database_dict=None)
                    data = GenericDataLoader.read_file(path)
                    self.vectorizer.add_document(path, data, self.lollms.config.data_vectorization_chunk_size, self.lollms.config.data_vectorization_overlap_size, add_first_line_to_all_chunks=True if path.suffix==".csv" else False)
                    self.vectorizer.index()
                    if callback is not None:
                        callback("File added successfully",MSG_TYPE.MSG_TYPE_INFO)
                    self.lollms.HideBlockingMessage(client.client_id)
                    return True
            except Exception as e:
                trace_exception(e)
                self.lollms.InfoMessage(f"Unsupported file format or empty file.\nSupported formats are {GenericDataLoader.get_supported_file_types()}",client_id=client.client_id)
                return False

    def load_message(self, id):
        """Gets a list of messages information

        Returns:
            list: List of entries in the format {"id":message id, "sender":sender name, "content":message content, "message_type":message type, "rank": message rank}
        """
        self.current_message = Message.from_db(self.discussions_db, id)
        return self.current_message
    
    def add_message(
                    self, 
                    message_type,
                    sender_type,
                    sender,
                    content,
                    metadata=None,
                    ui=None,
                    rank=0, 
                    parent_message_id=0, 
                    binding="", 
                    model ="", 
                    personality="", 
                    created_at=None, 
                    started_generating_at=None,
                    finished_generating_at=None,
                    nb_tokens=None
                ):
        """Adds a new message to the discussion

        Args:
            sender (str): The sender name
            content (str): The text sent by the sender

        Returns:
            int: The added message id
        """
        if created_at is None:
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if started_generating_at is None:
            started_generating_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if finished_generating_at is None:
            finished_generating_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if nb_tokens is None:
            nb_tokens = 0

        self.current_message = Message(
            self.discussion_id,
            self.discussions_db,
            message_type,
            sender_type,
            sender,
            content,
            metadata,
            ui,
            rank,
            parent_message_id,
            binding,
            model,
            personality,
            created_at,
            started_generating_at,
            finished_generating_at,
            nb_tokens,
            insert_into_db=True
        )

        self.messages.append(self.current_message)
        return self.current_message

    def rename(self, new_title):
        """Renames the discussion

        Args:
            new_title (str): The nex discussion name
        """
        self.discussions_db.update(
            f"UPDATE discussion SET title=? WHERE id=?",(new_title,self.discussion_id)
        )

    def title(self):
        """Renames the discussion

        Args:
            new_title (str): The nex discussion name
        """
        rows = self.discussions_db.select(
            f"Select title from discussion WHERE id={self.discussion_id}"
        )
        return rows[0][0]

    def delete_discussion(self):
        """Deletes the discussion
        """
        self.discussions_db.delete(
            f"DELETE FROM message WHERE discussion_id={self.discussion_id}"
        )
        self.discussions_db.delete(
            f"DELETE FROM discussion WHERE id={self.discussion_id}"
        )

    def get_messages(self):
        """Gets a list of messages information

        Returns:
            list: List of entries in the format {"id":message id, "sender":sender name, "content":message content, "message_type":message type, "rank": message rank}
        """
        columns = Message.get_fields()

        rows = self.discussions_db.select(
            f"SELECT {','.join(columns)} FROM message WHERE discussion_id=?", (self.discussion_id,)
        )
        msg_dict = [{ c:row[i] for i,c in enumerate(columns)} for row in rows]
        self.messages=[]
        for msg in msg_dict:
            self.messages.append(Message.from_dict(self.discussions_db, msg))

        if len(self.messages)>0:
            self.current_message = self.messages[-1]

        return self.messages

    def get_message(self, message_id):
        for message in self.messages:
            if message.id == int(message_id):
                self.current_message = message
                return message
        return None

    def select_message(self, message_id):
        msg = self.get_message(message_id)
        if msg is not None:
            self.current_message = msg
            return True
        else:
            return False 

    def update_message(self, new_content, new_metadata=None, new_ui=None, started_generating_at=None, nb_tokens=None):
        """Updates the content of a message

        Args:
            message_id (int): The id of the message to be changed
            new_content (str): The nex message content
        """
        self.current_message.update(new_content, new_metadata, new_ui, started_generating_at, nb_tokens)

    def edit_message(self, message_id, new_content, new_metadata=None, new_ui=None):
        """Edits the content of a message

        Args:
            message_id (int): The id of the message to be changed
            new_content (str): The nex message content
        """
        msg = self.get_message(message_id)
        if msg:
            msg.update(new_content, new_metadata, new_ui)
            return True
        else:
            return False


    def message_rank_up(self, message_id):
        """Increments the rank of the message

        Args:
            message_id (int): The id of the message to be changed
        """
        # Retrieve current rank value for message_id
        current_rank = self.discussions_db.select("SELECT rank FROM message WHERE id=?", (message_id,),False)[0]

        # Increment current rank value by 1
        new_rank = current_rank + 1        
        self.discussions_db.update(
            f"UPDATE message SET rank = ? WHERE id = ?",(new_rank,message_id)
        )
        return new_rank

    def message_rank_down(self, message_id):
        """Increments the rank of the message

        Args:
            message_id (int): The id of the message to be changed
        """
        # Retrieve current rank value for message_id
        current_rank = self.discussions_db.select("SELECT rank FROM message WHERE id=?", (message_id,),False)[0]

        # Increment current rank value by 1
        new_rank = current_rank - 1        
        self.discussions_db.update(
            f"UPDATE message SET rank = ? WHERE id = ?",(new_rank,message_id)
        )
        return new_rank
    
    def delete_message(self, message_id):
        """Delete the message

        Args:
            message_id (int): The id of the message to be deleted
        """
        # Retrieve current rank value for message_id
        self.discussions_db.delete("DELETE FROM message WHERE id=?", (message_id,))

    def export_for_vectorization(self):
        """
        Export all discussions and their messages from the database to a Markdown list format.

        Returns:
            list: A list of lists representing discussions and their messages in a Markdown format.
                Each inner list contains the discussion title and a string representing all
                messages in the discussion in a Markdown format.
        """        
        # Extract the title
        title = self.title()
        messages = ""
        # Iterate through messages in the discussion
        for message in self.messages:
            sender = message.sender
            content = message.content
            # Append the sender and content in a Markdown format
            messages += f'{sender}: {content}\n'
        return title, messages
 
    def format_discussion(self, max_allowed_tokens, splitter_text="!@>"):
        formatted_text = ""
        for message in reversed(self.messages):  # Start from the newest message
            formatted_message = f"{splitter_text}{message.sender.replace(':','').replace('!@>','')}:\n{message.content}\n"
            tokenized_message = self.lollms.model.tokenize(formatted_message)
            if len(tokenized_message) + len(self.lollms.model.tokenize(formatted_text)) <= max_allowed_tokens:
                formatted_text = formatted_message + formatted_text
            else:
                break  # Stop if adding the next message would exceed the limit
        return formatted_text   
# ========================================================================================================================
