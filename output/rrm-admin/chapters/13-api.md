## 13 API

Взаимодействие РОСА Менеджер ресурсов с другими программными продуктами осуществляется с помощью API.

API состоит из ряда методов, которые условно сгруппированы в отдельные API. Каждый метод выполняет одну отдельную задачу.

Через API можно управлять:

владельцами ресурсов;

ролями;

аутентификацией.

### 13.1 Назначение владельца ресурса

Назначение владения ресурсами осуществляется с помощью действия set_ownership. Это действие доступно для следующих ресурсов:

/api/auth_key_pairs;

/api/cloud_templates;

/api/instances;

/api/service_templates

/api/services;

/api/templates;

/api/vms.

#### 13.1.1 Назначение владельца

Назначение владельца в запросах осуществляется через спецификации owner и group:

{

"owner" : { "href" : "http://localhost:3000/api/users/:id" },

"group" : { "href" : "http://localhost:3000/api/groups/:id" }

}

Примечание:

Назначить владельца можно через href, id, name или userid.

Назначить группу можно через href, id или description.

Назначение владельца может быть выполнено для определенного ресурса или нескольких ресурсов в одном запросе.

###### 13.1.1.0.1 Пример назначения владельца на единичный ресурс

Запрос:

POST /api/vms/320

{

"action" : "set_ownership",

"resource" : {

"owner" : { "userid" : "jdoe" },

"group" : { "description" : "TestGroup" }

}

}

Ответ:

{

"success": true,

"message": "setting ownership of vms id 320 to owner: jdoe, group: TestGroup",

"href": "http://localhost:3000/api/vms/320"

}

###### 13.1.1.0.2 Пример назначения владельца на несколько ресурсов в одном запросе

Запрос:

POST /api/services

{

"action" : "set_ownership",

"resources" : [

{ "href" : "http://localhost:3000/api/services/104", "owner" : { "name" : "John Doe" } },

{ "href" : "http://localhost:3000/api/services/105", "owner" : { "name" : "John Doe" } },

{ "href" : "http://localhost:3000/api/services/106", "owner" : { "name" : "John Doe" } }

]

}

Ответ:

{

"results": [

{

"success": true,

"message": "setting ownership of services id 104 to owner: John Doe",

"href": "http://localhost:3000/api/services/104"

},

{

"success": true,

"message": "setting ownership of services id 105 to owner: John Doe",

"href": "http://localhost:3000/api/services/105"

},

{

"success": true,

"message": "setting ownership of services id 106 to owner: John Doe",

"href": "http://localhost:3000/api/services/106"

}

}

### 13.2 Управление ролями

Управление ролями пользователей осуществляется через коллекцию /api/roles, а также связанные с ним функции посредством /api/features.

Доступны полные действия CRUD над ролями:

запрос ролей;

создание ролей;

редактирование ролей;

удаление ролей.

#### 13.2.1 Запрос ролей

Опрос всех ролей в Комплексе:

GET /api/roles

Получение подробной информации о конкретной роли:

GET /api/roles/:id

Получение подробной информации о конкретной роли, включая предоставленные права:

GET /api/roles/:id?expand=features

или с запросом прав, назначенных ролью:

GET /api/roles/:id/features?expand=resources

Запрос всех прав в Комплексе, которые можно назначить роли:

GET /api/features

#### 13.2.2 Создание ролей

Роли можно создавать с помощью POST в коллекции ролей или с помощью действия create, которое также позволяет создавать несколько ролей в одном запросе:

POST /api/roles

{

"action" : "create",

"resource" : {

"name" : "sample_role",

"settings" : { "restrictions" : { "vms" : "user" } },

"features" : [

{ "identifier" : "vm_explorer" },

{ "identifier" : "ems_infra_tag" },

{ "identifier" : "miq_report_run" }

]

}

}

Примечание – restrictions для ВМ могут быть любыми из user или user_or_group.

Права могут быть указаны через identifier, href, id или создание нескольких ролей:

{

"action" : "create",

"resources" : [

{ "name" : "sample_role1", ... },

{ "name" : "sample_role2", ... },

...

]

}

#### 13.2.3 Редактирование ролей

Редактирование единственной роли:

POST /api/roles/:id

{

"action" : "edit",

"resource" : {

"name" : "updated_sample_role",

"settings" : { "restrictions" : { "vms" : "user_or_group" } }

}

}

Редактирование нескольких ролей:

POST /api/roles

{

"action" : "edit",

"resources" : [

{

"href" : "http://localhost:3000/api/roles/101",

"name" : "updated_sample_role1"

},

{

"href" : "http://localhost:3000/api/roles/102",

"name" : "updated_sample_role2"

},

...

]

}

Назначение прав для роли:

POST /api/roles/:id/features

{

"action" : "assign",

"resource" : {

"identifier" : "miq_request_view"

}

}

Назначение прав для нескольких ролей:

{

"action" : "assign",

"resources" : [

{ "identifier" : "miq_request_view" },

{ "identifier" : "storage_manager_show_list" },

...

]

}

Отмена назначения прав для роли:

POST /api/roles/:id/features

{

"action" : "unassign",

"resource" : {

{ "identifier" : "miq_request_view" }

}

}

Отмена назначения прав для нескольких ролей:

{

"action" : "unassign",

"resources" : [

{ "identifier" : "miq_request_view" },

{ "identifier" : "storage_manager_show_list" },

...

]

}

#### 13.2.4 Удаление ролей

Несистемные роли (т. е. не read_only) можно удалить либо с помощью действия delete POST, либо с помощью HTTP-метода DELETE соответственно:

POST /api/roles/101

{

"action" : "delete"

}

или

DELETE /api/roles/101

Удаление нескольких ролей можно выполнить следующим образом:

POST /api/roles

{

"action" : "delete",

"resources" : [

{ "href" : "http://localhost:3000/api/roles/101" },

{ "href" : "http://localhost:3000/api/roles/102" },

...

]

}

### 13.3 Управление аутентификацией

Управление аутентификациями осуществляется через коллекцию /api/authentications.

Доступны полные действия CRUD при аутентификации:

запрос аутентификаций;

создание аутентификаций;

редактирование аутентификаций;

обновление аутентификаций;

удаление аутентификаций.

#### 13.3.1 Запрос аутентификаций

Запрос всех аутентификаций в Комплексе:

GET /api/authentications

Получение подробной информации о конкретной аутентификации:

GET /api/authentications/:id

Можно также запросить аутентификацию менеджера полезной нагрузки сценария конфигурации следующим образом:

GET /api/configuration_script_payloads/:id/authentications

или получить подробную информацию о конкретной аутентификации:

GET /api/configuration_script_payloads/:id/authentications/:authentication_id

#### 13.3.2 Создание аутентификаций

Аутентификацию можно создать с помощью POST для коллекции аутентификаций или с помощью подписи действия create, которое также позволяет создавать несколько аутентификаций в одном запросе.

POST /api/authentications

{

"description" : "Authentication Description",

"name" : "SomeCredentials",

"related" : {},

"type" : "Комплекса::Providers::AnsibleTower::AutomationManager::Credential",

"manager_resource" : { "href" : "http://localhost:3000/api/providers/7" }

}

Создание нескольких аутентификаций:

{

"action" : "create",

"resources" : [

{ "description" : "System Credentials", "name" : "SystemCreds", ... },

{ "description" : "Admin Credentials", "name" : "AdminCreds", ... },

...

]

}

При необходимости можно создать аутентификацию для поставщика конкретного сценария конфигурации, что устраняет необходимость указания поставщика:

POST /api/configuration_script_payloads/:id/authentications

{

"description" : "Authentication Description",

"name" : "SomeCredentials",

"related" : {},

"type" : "Комплекса::Providers::AnsibleTower::AutomationManager::Credential"

}

Также с поддержкой массового создания:

{

"action" : "create",

"resources" : [

{ "description" : "System Credentials", "name" : "SystemCreds", ... },

{ "description" : "Admin Credentials", "name" : "AdminCreds", ... },

...

]

}

#### 13.3.3 Редактирование аутентификаций

Редактирование одной аутентификации:

POST /api/authentications/:id

{

"action" : "edit",

"resource" : {

"name" : "UpdatedCredentials"

}

}

Редактирование нескольких аутентификаций:

POST /api/authentications

{

"action" : "edit",

"resources" : [

{

"href" : "http://localhost:3000/api/authentications/101",

"description" : "Updated Sample Credentials 1",

"name" : "UpdatedCredentials1"

},

{

"href" : "http://localhost:3000/api/authentications/102",

"description" : "Updated Sample Credentials 2",

"name" : "UpdatedCredentials2"

},

...

]

}

#### 13.3.4 Обновление аутентификаций

Аутентификацию можно обновить, отправив действие refresh на один ресурс или на несколько ресурсов одновременно, с использованием коллекции:

POST /api/authentications/:id

{

"action" : "refresh"

}

Обновление нескольких аутентификаций:

POST /api/authentications

{

"action" : "refresh",

"resources" : [

{ "id" : "51" },

{ "id" : "52" }

]

}

Например, запрос:

POST /api/authentications/51

{

"action" : "refresh"

}

Ответ:

{

"success" : true,

"message" : "Refreshing Authentication id:51 name:'SampleCredentials'",

"task_id" : "8",

"task_href" : "http://localhost:3000/api/tasks/8",

"tasks" : [

{

"id" : "8",

"href" : "http://localhost:3000/api/tasks/8"

}

]

}

#### 13.3.5 Удаление аутентификаций

Аутентификацию можно удалить либо с помощью действия delete POST, либо с помощью HTTP-метода DELETE:

POST /api/authentications/101

{

"action" : "delete"

}

или:

DELETE /api/authentications/101

Удаление нескольких аутентификаций можно выполнить следующим образом:

POST /api/authentications

{

"action" : "delete",

"resources" : [

{ "href" : "http://localhost:3000/api/authentications/101" },

{ "href" : "http://localhost:3000/api/authentications/102" },

...

]

}

Перечень терминов

Перечень сокращений