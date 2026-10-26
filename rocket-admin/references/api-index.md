# Rocket.Chat REST API Index

- **Live source**: `https://rocket.codimeo.com/api/docs/json`
- **Server version**: 8.9
- **OpenAPI**: 3.0.3
- **Operations**: 693 across 648 paths
- **Generated**: 2026-10-17

Undocumented routes are marked with a dagger (†). They only appear when the spec is fetched with `?withUndocumented=true`.

For full parameter, request-body, and response detail:

```bash
bash scripts/rc-doc.sh <family>.<action>
```

## Families

| Family | Operations |
|---|---:|
| `livechat` | 147 |
| `users` | 48 |
| `channels` | 42 |
| `apps` | 40 |
| `groups` | 38 |
| `rooms` | 37 |
| `chat` | 29 |
| `omnichannel` | 19 |
| `teams` | 19 |
| `abac` | 15 |
| `dm` | 15 |
| `im` | 15 |
| `video-conference` | 15 |
| `e2e` | 11 |
| `cloud` | 10 |
| `moderation` | 10 |
| `engagement-dashboard` | 9 |
| `roles` | 9 |
| `settings` | 9 |
| `integrations` | 8 |
| `calendar-events` | 6 |
| `canned-responses` | 6 |
| `email-inbox` | 6 |
| `sessions` | 6 |
| `audit` | 5 |
| `commands` | 5 |
| `custom-sounds` | 5 |
| `emoji-custom` | 5 |
| `import` | 5 |
| `oauth-apps` | 5 |
| `push` | 5 |
| `autotranslate` | 4 |
| `custom-user-status` | 4 |
| `experimental` | 4 |
| `licenses` | 4 |
| `media-calls` | 4 |
| `permissions` | 4 |
| `subscriptions` | 4 |
| `ai` | 3 |
| `banners` | 3 |
| `ldap` | 3 |
| `statistics` | 3 |
| `` | 2 |
| `assets` | 2 |
| `call-history` | 2 |
| `logout` | 2 |
| `mailer` | 2 |
| `method` | 2 |
| `presence` | 2 |
| `twoFactorChallenges` | 2 |
| `webdav` | 2 |
| `directory` | 1 |
| `downloadPendingAvatars` | 1 |
| `downloadPendingFiles` | 1 |
| `downloadPublicImportFile` | 1 |
| `federation` | 1 |
| `findOrCreateInvite` | 1 |
| `fingerprint` | 1 |
| `getCurrentImportOperation` | 1 |
| `getImportFileData` | 1 |
| `getImportProgress` | 1 |
| `getLatestImportOperations` | 1 |
| `importers` | 1 |
| `instances` | 1 |
| `listInvites` | 1 |
| `login` | 1 |
| `loginCode` | 1 |
| `me` | 1 |
| `pw` | 1 |
| `removeInvite` | 1 |
| `saml` | 1 |
| `sendInvitationEmail` | 1 |
| `service` | 1 |
| `setupWizard` | 1 |
| `shield` | 1 |
| `smtp` | 1 |
| `spotlight` | 1 |
| `startImport` | 1 |
| `uploadImportFile` | 1 |
| `uploads` | 1 |
| `useInviteToken` | 1 |
| `validateInviteToken` | 1 |

## livechat

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/livechat/:rid/messages` † | :rid/messages |
| GET | `/api/v1/livechat/agent.info/:rid/:token` † | agent.info/:rid/:token |
| GET | `/api/v1/livechat/agent.next/:token` † | agent.next/:token |
| POST | `/api/v1/livechat/agent.status` † | agent.status |
| POST | `/api/v1/livechat/agents.saveInfo` | agents.saveInfo |
| GET | `/api/v1/livechat/agents/:agentId/departments` † | agents/:agentId/departments |
| GET | `/api/v1/livechat/analytics/agent-overview` † | analytics/agent-overview |
| GET | `/api/v1/livechat/analytics/agents/available-for-service-history` † | analytics/agents/available-for-service-history |
| GET | `/api/v1/livechat/analytics/agents/average-service-time` † | analytics/agents/average-service-time |
| GET | `/api/v1/livechat/analytics/agents/total-service-time` † | analytics/agents/total-service-time |
| GET | `/api/v1/livechat/analytics/dashboards/agents-productivity-totalizers` † | analytics/dashboards/agents-productivity-totalizers |
| GET | `/api/v1/livechat/analytics/dashboards/charts-data` | analytics/dashboards/charts-data |
| GET | `/api/v1/livechat/analytics/dashboards/charts/agents-status` † | analytics/dashboards/charts/agents-status |
| GET | `/api/v1/livechat/analytics/dashboards/charts/chats` † | analytics/dashboards/charts/chats |
| GET | `/api/v1/livechat/analytics/dashboards/charts/chats-per-agent` † | analytics/dashboards/charts/chats-per-agent |
| GET | `/api/v1/livechat/analytics/dashboards/charts/chats-per-department` † | analytics/dashboards/charts/chats-per-department |
| GET | `/api/v1/livechat/analytics/dashboards/charts/timings` † | analytics/dashboards/charts/timings |
| GET | `/api/v1/livechat/analytics/dashboards/chats-totalizers` † | analytics/dashboards/chats-totalizers |
| GET | `/api/v1/livechat/analytics/dashboards/conversation-totalizers` † | analytics/dashboards/conversation-totalizers |
| GET | `/api/v1/livechat/analytics/dashboards/conversations-by-agent` † | analytics/dashboards/conversations-by-agent |
| GET | `/api/v1/livechat/analytics/dashboards/conversations-by-department` † | analytics/dashboards/conversations-by-department |
| GET | `/api/v1/livechat/analytics/dashboards/conversations-by-source` † | analytics/dashboards/conversations-by-source |
| GET | `/api/v1/livechat/analytics/dashboards/conversations-by-status` † | analytics/dashboards/conversations-by-status |
| GET | `/api/v1/livechat/analytics/dashboards/conversations-by-tags` † | analytics/dashboards/conversations-by-tags |
| GET | `/api/v1/livechat/analytics/dashboards/productivity-totalizers` † | analytics/dashboards/productivity-totalizers |
| GET | `/api/v1/livechat/analytics/departments/amount-of-chats` † | analytics/departments/amount-of-chats |
| GET | `/api/v1/livechat/analytics/departments/average-chat-duration-time` † | analytics/departments/average-chat-duration-time |
| GET | `/api/v1/livechat/analytics/departments/average-service-time` † | analytics/departments/average-service-time |
| GET | `/api/v1/livechat/analytics/departments/average-waiting-time` † | analytics/departments/average-waiting-time |
| GET | `/api/v1/livechat/analytics/departments/percentage-abandoned-chats` † | analytics/departments/percentage-abandoned-chats |
| GET | `/api/v1/livechat/analytics/departments/total-abandoned-chats` † | analytics/departments/total-abandoned-chats |
| GET | `/api/v1/livechat/analytics/departments/total-service-time` † | analytics/departments/total-service-time |
| GET | `/api/v1/livechat/analytics/departments/total-transferred-chats` † | analytics/departments/total-transferred-chats |
| GET | `/api/v1/livechat/analytics/overview` † | analytics/overview |
| GET | `/api/v1/livechat/appearance` † | appearance |
| POST | `/api/v1/livechat/appearance` † | appearance |
| GET | `/api/v1/livechat/business-hour` † | business-hour |
| GET | `/api/v1/livechat/business-hours` † | business-hours |
| POST | `/api/v1/livechat/business-hours.remove` | business-hours.remove |
| POST | `/api/v1/livechat/business-hours.save` | business-hours.save |
| GET | `/api/v1/livechat/config` † | config |
| GET | `/api/v1/livechat/config/routing` | config/routing |
| GET | `/api/v1/livechat/custom-fields` † | custom-fields |
| POST | `/api/v1/livechat/custom-fields.delete` | custom-fields.delete |
| POST | `/api/v1/livechat/custom-fields.save` | custom-fields.save |
| GET | `/api/v1/livechat/custom-fields/:_id` † | custom-fields/:_id |
| POST | `/api/v1/livechat/custom.field` † | custom.field |
| POST | `/api/v1/livechat/custom.fields` † | custom.fields |
| GET | `/api/v1/livechat/department` † | department |
| POST | `/api/v1/livechat/department` † | department |
| GET | `/api/v1/livechat/department.autocomplete` † | department.autocomplete |
| GET | `/api/v1/livechat/department.listByIds` † | department.listByIds |
| DELETE | `/api/v1/livechat/department/:_id` † | department/:_id |
| GET | `/api/v1/livechat/department/:_id` † | department/:_id |
| PUT | `/api/v1/livechat/department/:_id` † | department/:_id |
| GET | `/api/v1/livechat/department/:_id/agents` † | department/:_id/agents |
| POST | `/api/v1/livechat/department/:_id/agents` † | department/:_id/agents |
| POST | `/api/v1/livechat/department/:_id/archive` † | department/:_id/archive |
| POST | `/api/v1/livechat/department/:_id/unarchive` † | department/:_id/unarchive |
| GET | `/api/v1/livechat/department/isDepartmentCreationAvailable` † | department/isDepartmentCreationAvailable |
| GET | `/api/v1/livechat/departments/archived` † | departments/archived |
| GET | `/api/v1/livechat/inquiries.getOne` † | inquiries.getOne |
| GET | `/api/v1/livechat/inquiries.list` † | inquiries.list |
| GET | `/api/v1/livechat/inquiries.queuedForUser` † | inquiries.queuedForUser |
| POST | `/api/v1/livechat/inquiries.returnAsInquiry` | inquiries.returnAsInquiry |
| POST | `/api/v1/livechat/inquiries.take` † | inquiries.take |
| PUT | `/api/v1/livechat/inquiry.setSLA` † | inquiry.setSLA |
| GET | `/api/v1/livechat/integrations.settings` † | integrations.settings |
| POST | `/api/v1/livechat/message` † | message |
| DELETE | `/api/v1/livechat/message/:_id` † | message/:_id |
| GET | `/api/v1/livechat/message/:_id` † | message/:_id |
| PUT | `/api/v1/livechat/message/:_id` † | message/:_id |
| POST | `/api/v1/livechat/messages` † | messages |
| GET | `/api/v1/livechat/messages.history/:rid` † | messages.history/:rid |
| GET | `/api/v1/livechat/monitors` † | monitors |
| POST | `/api/v1/livechat/monitors.create` | monitors.create |
| POST | `/api/v1/livechat/monitors.delete` | monitors.delete |
| GET | `/api/v1/livechat/monitors/:username` † | monitors/:username |
| POST | `/api/v1/livechat/offline.message` † | offline.message |
| POST | `/api/v1/livechat/page.visited` † | page.visited |
| GET | `/api/v1/livechat/priorities` † | priorities |
| GET | `/api/v1/livechat/priorities.reset` † | priorities.reset |
| POST | `/api/v1/livechat/priorities.reset` † | priorities.reset |
| GET | `/api/v1/livechat/priorities/:priorityId` † | priorities/:priorityId |
| PUT | `/api/v1/livechat/priorities/:priorityId` † | priorities/:priorityId |
| GET | `/api/v1/livechat/queue` † | queue |
| GET | `/api/v1/livechat/room` † | room |
| POST | `/api/v1/livechat/room.close` † | room.close |
| POST | `/api/v1/livechat/room.closeByUser` † | room.closeByUser |
| POST | `/api/v1/livechat/room.forward` † | room.forward |
| GET | `/api/v1/livechat/room.join` † | room.join |
| POST | `/api/v1/livechat/room.onHold` † | room.onHold |
| POST | `/api/v1/livechat/room.resumeOnHold` † | room.resumeOnHold |
| POST | `/api/v1/livechat/room.saveInfo` † | room.saveInfo |
| POST | `/api/v1/livechat/room.survey` † | room.survey |
| DELETE | `/api/v1/livechat/room/:rid/priority` † | room/:rid/priority |
| POST | `/api/v1/livechat/room/:rid/priority` † | room/:rid/priority |
| GET | `/api/v1/livechat/rooms` † | rooms |
| POST | `/api/v1/livechat/rooms.delete` | rooms.delete |
| POST | `/api/v1/livechat/rooms.removeAllClosedRooms` | rooms.removeAllClosedRooms |
| GET | `/api/v1/livechat/rooms/filters` † | rooms/filters |
| GET | `/api/v1/livechat/sla` † | sla |
| POST | `/api/v1/livechat/sla` † | sla |
| DELETE | `/api/v1/livechat/sla/:slaId` † | sla/:slaId |
| GET | `/api/v1/livechat/sla/:slaId` † | sla/:slaId |
| PUT | `/api/v1/livechat/sla/:slaId` † | sla/:slaId |
| POST | `/api/v1/livechat/sms-incoming/:service` † | sms-incoming/:service |
| GET | `/api/v1/livechat/tags` † | tags |
| POST | `/api/v1/livechat/tags.delete` | tags.delete |
| POST | `/api/v1/livechat/tags.save` | tags.save |
| GET | `/api/v1/livechat/tags/:tagId` † | tags/:tagId |
| POST | `/api/v1/livechat/transcript` † | transcript |
| DELETE | `/api/v1/livechat/transcript/:rid` † | transcript/:rid |
| POST | `/api/v1/livechat/transcript/:rid` † | transcript/:rid |
| GET | `/api/v1/livechat/transfer.history/:rid` † | transfer.history/:rid |
| GET | `/api/v1/livechat/triggers` † | triggers |
| POST | `/api/v1/livechat/triggers` † | triggers |
| DELETE | `/api/v1/livechat/triggers/:_id` † | triggers/:_id |
| GET | `/api/v1/livechat/triggers/:_id` † | triggers/:_id |
| POST | `/api/v1/livechat/triggers/:_id/external-service/call` † | triggers/:_id/external-service/call |
| POST | `/api/v1/livechat/triggers/external-service/test` † | triggers/external-service/test |
| GET | `/api/v1/livechat/units` † | units |
| POST | `/api/v1/livechat/units` † | units |
| DELETE | `/api/v1/livechat/units/:id` † | units/:id |
| GET | `/api/v1/livechat/units/:id` † | units/:id |
| POST | `/api/v1/livechat/units/:id` † | units/:id |
| GET | `/api/v1/livechat/units/:unitId/departments` † | units/:unitId/departments |
| GET | `/api/v1/livechat/units/:unitId/departments/available` † | units/:unitId/departments/available |
| GET | `/api/v1/livechat/units/:unitId/monitors` † | units/:unitId/monitors |
| POST | `/api/v1/livechat/upload/:rid` † | upload/:rid |
| GET | `/api/v1/livechat/users/:type` † | users/:type |
| POST | `/api/v1/livechat/users/:type` † | users/:type |
| DELETE | `/api/v1/livechat/users/:type/:_id` † | users/:type/:_id |
| GET | `/api/v1/livechat/users/:type/:_id` † | users/:type/:_id |
| POST | `/api/v1/livechat/visitor` † | visitor |
| POST | `/api/v1/livechat/visitor.status` † | visitor.status |
| DELETE | `/api/v1/livechat/visitor/:token` † | visitor/:token |
| GET | `/api/v1/livechat/visitor/:token` † | visitor/:token |
| GET | `/api/v1/livechat/visitor/:token/room` † | visitor/:token/room |
| POST | `/api/v1/livechat/visitor/department.transfer` | visitor/department.transfer |
| GET | `/api/v1/livechat/visitors.autocomplete` † | visitors.autocomplete |
| GET | `/api/v1/livechat/visitors.chatHistory/room/:roomId/visitor/:visitorId` † | visitors.chatHistory/room/:roomId/visitor/:visitorId |
| GET | `/api/v1/livechat/visitors.info` † | visitors.info |
| GET | `/api/v1/livechat/visitors.pagesVisited/:roomId` † | visitors.pagesVisited/:roomId |
| GET | `/api/v1/livechat/visitors.search` † | visitors.search |
| GET | `/api/v1/livechat/visitors.searchChats/room/:roomId/visitor/:visitorId` † | visitors.searchChats/room/:roomId/visitor/:visitorId |
| POST | `/api/v1/livechat/webhook.test` † | webhook.test |

## users

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/users.2fa.disableEmail` | 2fa.disableEmail |
| POST | `/api/v1/users.2fa.enableEmail` | 2fa.enableEmail |
| POST | `/api/v1/users.2fa.sendEmailCode` | 2fa.sendEmailCode |
| GET | `/api/v1/users.autocomplete` | autocomplete |
| GET | `/api/v1/users.checkUsernameAvailability` | checkUsernameAvailability |
| POST | `/api/v1/users.create` | create |
| POST | `/api/v1/users.createToken` | createToken |
| POST | `/api/v1/users.deactivateIdle` | deactivateIdle |
| POST | `/api/v1/users.delete` | delete |
| POST | `/api/v1/users.deleteOwnAccount` | deleteOwnAccount |
| POST | `/api/v1/users.disableTotp` | disableTotp |
| POST | `/api/v1/users.enableTotp` | enableTotp |
| POST | `/api/v1/users.forgotPassword` | forgotPassword |
| POST | `/api/v1/users.generatePersonalAccessToken` | generatePersonalAccessToken |
| GET | `/api/v1/users.getAvatar` † | getAvatar |
| GET | `/api/v1/users.getAvatarSuggestion` | getAvatarSuggestion |
| GET | `/api/v1/users.getPersonalAccessTokens` | getPersonalAccessTokens |
| GET | `/api/v1/users.getPreferences` | getPreferences |
| GET | `/api/v1/users.getPresence` | getPresence |
| GET | `/api/v1/users.getStatus` | getStatus |
| GET | `/api/v1/users.getUsernameSuggestion` | getUsernameSuggestion |
| GET | `/api/v1/users.info` | info |
| GET | `/api/v1/users.list` † | list |
| GET | `/api/v1/users.listByStatus` | listByStatus |
| GET | `/api/v1/users.listTeams` | listTeams |
| POST | `/api/v1/users.logout` | logout |
| POST | `/api/v1/users.logoutOtherClients` | logoutOtherClients |
| GET | `/api/v1/users.presence` | presence |
| POST | `/api/v1/users.regeneratePersonalAccessToken` | regeneratePersonalAccessToken |
| POST | `/api/v1/users.regenerateTotpCodes` | regenerateTotpCodes |
| POST | `/api/v1/users.register` | register |
| POST | `/api/v1/users.removeOtherTokens` | removeOtherTokens |
| POST | `/api/v1/users.removePersonalAccessToken` | removePersonalAccessToken |
| GET | `/api/v1/users.requestDataDownload` | requestDataDownload |
| POST | `/api/v1/users.resetAvatar` | resetAvatar |
| POST | `/api/v1/users.resetE2EKey` | resetE2EKey |
| POST | `/api/v1/users.resetTOTP` | resetTOTP |
| POST | `/api/v1/users.sendConfirmationEmail` | sendConfirmationEmail |
| POST | `/api/v1/users.sendWelcomeEmail` | sendWelcomeEmail |
| POST | `/api/v1/users.setActiveStatus` | setActiveStatus |
| POST | `/api/v1/users.setAvatar` | setAvatar |
| POST | `/api/v1/users.setPreferences` | setPreferences |
| POST | `/api/v1/users.setStatus` | setStatus |
| GET | `/api/v1/users.totpCodesRemaining` | totpCodesRemaining |
| POST | `/api/v1/users.update` | update |
| POST | `/api/v1/users.updateOwnBasicInfo` | updateOwnBasicInfo |
| POST | `/api/v1/users.validateTotp` | validateTotp |
| POST | `/api/v1/users.verifyEmail` | verifyEmail |

## channels

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/channels.addAll` | addAll |
| POST | `/api/v1/channels.addLeader` | addLeader |
| POST | `/api/v1/channels.addModerator` | addModerator |
| POST | `/api/v1/channels.addOwner` | addOwner |
| GET | `/api/v1/channels.anonymousread` | anonymousread |
| POST | `/api/v1/channels.archive` | archive |
| POST | `/api/v1/channels.close` | close |
| POST | `/api/v1/channels.convertToTeam` | convertToTeam |
| GET | `/api/v1/channels.counters` | counters |
| POST | `/api/v1/channels.create` | create |
| POST | `/api/v1/channels.delete` | delete |
| GET | `/api/v1/channels.files` | files |
| GET | `/api/v1/channels.getAllUserMentionsByChannel` | getAllUserMentionsByChannel |
| GET | `/api/v1/channels.getIntegrations` | getIntegrations |
| GET | `/api/v1/channels.history` | history |
| GET | `/api/v1/channels.info` | info |
| POST | `/api/v1/channels.invite` | invite |
| POST | `/api/v1/channels.join` | join |
| POST | `/api/v1/channels.kick` | kick |
| POST | `/api/v1/channels.leave` | leave |
| GET | `/api/v1/channels.list` | list |
| GET | `/api/v1/channels.list.joined` | list.joined |
| GET | `/api/v1/channels.members` | members |
| GET | `/api/v1/channels.messages` | messages |
| GET | `/api/v1/channels.moderators` | moderators |
| GET | `/api/v1/channels.online` | online |
| POST | `/api/v1/channels.open` | open |
| POST | `/api/v1/channels.removeLeader` | removeLeader |
| POST | `/api/v1/channels.removeModerator` | removeModerator |
| POST | `/api/v1/channels.removeOwner` | removeOwner |
| POST | `/api/v1/channels.rename` | rename |
| GET | `/api/v1/channels.roles` | roles |
| POST | `/api/v1/channels.setAnnouncement` | setAnnouncement |
| POST | `/api/v1/channels.setCustomFields` | setCustomFields |
| POST | `/api/v1/channels.setDefault` | setDefault |
| POST | `/api/v1/channels.setDescription` | setDescription |
| POST | `/api/v1/channels.setJoinCode` | setJoinCode |
| POST | `/api/v1/channels.setPurpose` | setPurpose |
| POST | `/api/v1/channels.setReadOnly` | setReadOnly |
| POST | `/api/v1/channels.setTopic` | setTopic |
| POST | `/api/v1/channels.setType` | setType |
| POST | `/api/v1/channels.unarchive` | unarchive |

## apps

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/apps/` † |  |
| GET | `/api/apps//:id/export-logs` | /:id/export-logs |
| DELETE | `/api/apps/:id` † | :id |
| GET | `/api/apps/:id` † | :id |
| POST | `/api/apps/:id` † | :id |
| GET | `/api/apps/:id/apis` † | :id/apis |
| GET | `/api/apps/:id/icon` † | :id/icon |
| GET | `/api/apps/:id/languages` † | :id/languages |
| GET | `/api/apps/:id/logs` | :id/logs |
| GET | `/api/apps/:id/logs/distinctValues` | :id/logs/distinctValues |
| GET | `/api/apps/:id/screenshots` † | :id/screenshots |
| GET | `/api/apps/:id/settings` † | :id/settings |
| POST | `/api/apps/:id/settings` † | :id/settings |
| GET | `/api/apps/:id/settings/:settingId` † | :id/settings/:settingId |
| POST | `/api/apps/:id/settings/:settingId` † | :id/settings/:settingId |
| GET | `/api/apps/:id/status` † | :id/status |
| POST | `/api/apps/:id/status` † | :id/status |
| POST | `/api/apps/:id/sync` † | :id/sync |
| GET | `/api/apps/:id/versions` † | :id/versions |
| GET | `/api/apps/actionButtons` † | actionButtons |
| GET | `/api/apps/app-request` † | app-request |
| POST | `/api/apps/app-request/markAsSeen` † | app-request/markAsSeen |
| GET | `/api/apps/app-request/stats` † | app-request/stats |
| GET | `/api/apps/buildExternalAppRequest` † | buildExternalAppRequest |
| GET | `/api/apps/buildExternalUrl` † | buildExternalUrl |
| GET | `/api/apps/bundles/:id/apps` † | bundles/:id/apps |
| GET | `/api/apps/categories` † | categories |
| GET | `/api/apps/count` † | count |
| POST | `/api/apps/externalComponentEvent` † | externalComponentEvent |
| GET | `/api/apps/externalComponents` † | externalComponents |
| GET | `/api/apps/featured-apps` † | featured-apps |
| GET | `/api/apps/incompatibleModal` † | incompatibleModal |
| GET | `/api/apps/installed` † | installed |
| GET | `/api/apps/languages` † | languages |
| POST | `/api/apps/login` † | login |
| GET | `/api/apps/logout` † | logout |
| POST | `/api/apps/logout` † | logout |
| GET | `/api/apps/logs` | logs |
| GET | `/api/apps/marketplace` † | marketplace |
| POST | `/api/apps/notify-admins` † | notify-admins |

## groups

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/groups.addAll` | addAll |
| POST | `/api/v1/groups.addLeader` | addLeader |
| POST | `/api/v1/groups.addModerator` | addModerator |
| POST | `/api/v1/groups.addOwner` | addOwner |
| POST | `/api/v1/groups.archive` | archive |
| POST | `/api/v1/groups.close` | close |
| POST | `/api/v1/groups.convertToTeam` | convertToTeam |
| GET | `/api/v1/groups.counters` | counters |
| POST | `/api/v1/groups.create` | create |
| POST | `/api/v1/groups.delete` | delete |
| GET | `/api/v1/groups.files` | files |
| GET | `/api/v1/groups.getIntegrations` | getIntegrations |
| GET | `/api/v1/groups.history` | history |
| GET | `/api/v1/groups.info` | info |
| POST | `/api/v1/groups.invite` | invite |
| POST | `/api/v1/groups.kick` | kick |
| POST | `/api/v1/groups.leave` | leave |
| GET | `/api/v1/groups.list` | list |
| GET | `/api/v1/groups.listAll` | listAll |
| GET | `/api/v1/groups.members` | members |
| GET | `/api/v1/groups.messages` | messages |
| GET | `/api/v1/groups.moderators` | moderators |
| GET | `/api/v1/groups.online` | online |
| POST | `/api/v1/groups.open` | open |
| POST | `/api/v1/groups.removeLeader` | removeLeader |
| POST | `/api/v1/groups.removeModerator` | removeModerator |
| POST | `/api/v1/groups.removeOwner` | removeOwner |
| POST | `/api/v1/groups.rename` | rename |
| GET | `/api/v1/groups.roles` | roles |
| POST | `/api/v1/groups.setAnnouncement` | setAnnouncement |
| POST | `/api/v1/groups.setCustomFields` | setCustomFields |
| POST | `/api/v1/groups.setDescription` | setDescription |
| POST | `/api/v1/groups.setEncrypted` | setEncrypted |
| POST | `/api/v1/groups.setPurpose` | setPurpose |
| POST | `/api/v1/groups.setReadOnly` | setReadOnly |
| POST | `/api/v1/groups.setTopic` | setTopic |
| POST | `/api/v1/groups.setType` | setType |
| POST | `/api/v1/groups.unarchive` | unarchive |

## rooms

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/rooms.adminRooms` | adminRooms |
| GET | `/api/v1/rooms.adminRooms.getRoom` | adminRooms.getRoom |
| GET | `/api/v1/rooms.adminRooms.privateRooms` | adminRooms.privateRooms |
| GET | `/api/v1/rooms.autocomplete.adminRooms` | autocomplete.adminRooms |
| GET | `/api/v1/rooms.autocomplete.availableForTeams` | autocomplete.availableForTeams |
| GET | `/api/v1/rooms.autocomplete.channelAndPrivate` | autocomplete.channelAndPrivate |
| GET | `/api/v1/rooms.autocomplete.channelAndPrivate.withPagination` | autocomplete.channelAndPrivate.withPagination |
| POST | `/api/v1/rooms.banUser` | banUser |
| GET | `/api/v1/rooms.bannedUsers` | bannedUsers |
| POST | `/api/v1/rooms.changeArchivationState` | changeArchivationState |
| POST | `/api/v1/rooms.cleanHistory` | cleanHistory |
| POST | `/api/v1/rooms.createDiscussion` | createDiscussion |
| POST | `/api/v1/rooms.delete` | delete |
| POST | `/api/v1/rooms.export` | export |
| POST | `/api/v1/rooms.favorite` | favorite |
| GET | `/api/v1/rooms.get` | get |
| GET | `/api/v1/rooms.getDiscussions` | getDiscussions |
| POST | `/api/v1/rooms.hide` | hide |
| GET | `/api/v1/rooms.history` | history |
| GET | `/api/v1/rooms.images` | images |
| GET | `/api/v1/rooms.info` | info |
| POST | `/api/v1/rooms.invite` | invite |
| GET | `/api/v1/rooms.isMember` | isMember |
| POST | `/api/v1/rooms.join` | join |
| POST | `/api/v1/rooms.leave` | leave |
| POST | `/api/v1/rooms.media/:rid` † | media |
| POST | `/api/v1/rooms.mediaConfirm/:rid/:fileId` † | mediaConfirm |
| GET | `/api/v1/rooms.membersOrderedByRole` | membersOrderedByRole |
| POST | `/api/v1/rooms.muteUser` | muteUser |
| GET | `/api/v1/rooms.nameExists` | nameExists |
| POST | `/api/v1/rooms.open` | open |
| GET | `/api/v1/rooms.roles` | roles |
| POST | `/api/v1/rooms.saveDraft` | saveDraft |
| POST | `/api/v1/rooms.saveNotification` | saveNotification |
| POST | `/api/v1/rooms.saveRoomSettings` | saveRoomSettings |
| POST | `/api/v1/rooms.unbanUser` | unbanUser |
| POST | `/api/v1/rooms.unmuteUser` | unmuteUser |

## chat

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/chat.delete` | delete |
| POST | `/api/v1/chat.followMessage` | followMessage |
| GET | `/api/v1/chat.getDeletedMessages` | getDeletedMessages |
| GET | `/api/v1/chat.getDiscussions` | getDiscussions |
| GET | `/api/v1/chat.getMentionedMessages` | getMentionedMessages |
| GET | `/api/v1/chat.getMessage` | getMessage |
| GET | `/api/v1/chat.getMessageReadReceipts` | getMessageReadReceipts |
| POST | `/api/v1/chat.getMessages` | getMessages |
| GET | `/api/v1/chat.getPinnedMessages` | getPinnedMessages |
| GET | `/api/v1/chat.getStarredMessages` | getStarredMessages |
| GET | `/api/v1/chat.getThreadMessages` | getThreadMessages |
| GET | `/api/v1/chat.getThreadsList` | getThreadsList |
| GET | `/api/v1/chat.getURLPreview` | getURLPreview |
| GET | `/api/v1/chat.ignoreUser` | ignoreUser |
| POST | `/api/v1/chat.pinMessage` | pinMessage |
| POST | `/api/v1/chat.postMessage` | postMessage |
| POST | `/api/v1/chat.react` | react |
| POST | `/api/v1/chat.readThread` | readThread |
| POST | `/api/v1/chat.reportMessage` | reportMessage |
| GET | `/api/v1/chat.search` | search |
| POST | `/api/v1/chat.sendMessage` | sendMessage |
| POST | `/api/v1/chat.starMessage` | starMessage |
| GET | `/api/v1/chat.syncMessages` | syncMessages |
| GET | `/api/v1/chat.syncThreadMessages` | syncThreadMessages |
| GET | `/api/v1/chat.syncThreadsList` | syncThreadsList |
| POST | `/api/v1/chat.unPinMessage` | unPinMessage |
| POST | `/api/v1/chat.unStarMessage` | unStarMessage |
| POST | `/api/v1/chat.unfollowMessage` | unfollowMessage |
| POST | `/api/v1/chat.update` | update |

## omnichannel

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/omnichannel/:rid/request-transcript` † | :rid/request-transcript |
| GET | `/api/v1/omnichannel/contact` † | contact |
| POST | `/api/v1/omnichannel/contact` † | contact |
| GET | `/api/v1/omnichannel/contact.search` † | contact.search |
| POST | `/api/v1/omnichannel/contacts` † | contacts |
| POST | `/api/v1/omnichannel/contacts.block` † | contacts.block |
| GET | `/api/v1/omnichannel/contacts.channels` † | contacts.channels |
| GET | `/api/v1/omnichannel/contacts.checkExistence` † | contacts.checkExistence |
| POST | `/api/v1/omnichannel/contacts.conflicts` † | contacts.conflicts |
| POST | `/api/v1/omnichannel/contacts.delete` | contacts.delete |
| GET | `/api/v1/omnichannel/contacts.get` † | contacts.get |
| GET | `/api/v1/omnichannel/contacts.history` † | contacts.history |
| GET | `/api/v1/omnichannel/contacts.search` † | contacts.search |
| POST | `/api/v1/omnichannel/contacts.unblock` † | contacts.unblock |
| POST | `/api/v1/omnichannel/contacts.update` † | contacts.update |
| POST | `/api/v1/omnichannel/integrations` † | integrations |
| GET | `/api/v1/omnichannel/outbound/providers` | outbound/providers |
| POST | `/api/v1/omnichannel/outbound/providers/:id/message` | outbound/providers/:id/message |
| GET | `/api/v1/omnichannel/outbound/providers/:id/metadata` | outbound/providers/:id/metadata |

## teams

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/teams.addMembers` | addMembers |
| POST | `/api/v1/teams.addRooms` | addRooms |
| GET | `/api/v1/teams.autocomplete` | autocomplete |
| POST | `/api/v1/teams.convertToChannel` | convertToChannel |
| POST | `/api/v1/teams.create` | create |
| POST | `/api/v1/teams.delete` | delete |
| GET | `/api/v1/teams.info` | info |
| POST | `/api/v1/teams.leave` | leave |
| GET | `/api/v1/teams.list` | list |
| GET | `/api/v1/teams.listAll` | listAll |
| GET | `/api/v1/teams.listChildren` | listChildren |
| GET | `/api/v1/teams.listRooms` | listRooms |
| GET | `/api/v1/teams.listRoomsOfUser` | listRoomsOfUser |
| GET | `/api/v1/teams.members` | members |
| POST | `/api/v1/teams.removeMember` | removeMember |
| POST | `/api/v1/teams.removeRoom` | removeRoom |
| POST | `/api/v1/teams.update` | update |
| POST | `/api/v1/teams.updateMember` | updateMember |
| POST | `/api/v1/teams.updateRoom` | updateRoom |

## abac

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/abac/attributes` | attributes |
| POST | `/api/v1/abac/attributes` | attributes |
| DELETE | `/api/v1/abac/attributes/:_id` | attributes/:_id |
| GET | `/api/v1/abac/attributes/:_id` | attributes/:_id |
| PUT | `/api/v1/abac/attributes/:_id` | attributes/:_id |
| GET | `/api/v1/abac/attributes/:key/is-in-use` | attributes/:key/is-in-use |
| GET | `/api/v1/abac/audit` | audit |
| GET | `/api/v1/abac/pdp/health` | pdp/health |
| GET | `/api/v1/abac/rooms` | rooms |
| DELETE | `/api/v1/abac/rooms/:rid/attributes` | rooms/:rid/attributes |
| POST | `/api/v1/abac/rooms/:rid/attributes` | rooms/:rid/attributes |
| DELETE | `/api/v1/abac/rooms/:rid/attributes/:key` | rooms/:rid/attributes/:key |
| POST | `/api/v1/abac/rooms/:rid/attributes/:key` | rooms/:rid/attributes/:key |
| PUT | `/api/v1/abac/rooms/:rid/attributes/:key` | rooms/:rid/attributes/:key |
| POST | `/api/v1/abac/users/sync` | users/sync |

## dm

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/dm.blockUser` | blockUser |
| POST | `/api/v1/dm.close` | close |
| GET | `/api/v1/dm.counters` | counters |
| POST | `/api/v1/dm.create` | create |
| POST | `/api/v1/dm.delete` | delete |
| GET | `/api/v1/dm.files` | files |
| GET | `/api/v1/dm.history` | history |
| POST | `/api/v1/dm.leave` | leave |
| GET | `/api/v1/dm.list` | list |
| GET | `/api/v1/dm.list.everyone` | list.everyone |
| GET | `/api/v1/dm.members` | members |
| GET | `/api/v1/dm.messages` | messages |
| GET | `/api/v1/dm.messages.others` | messages.others |
| POST | `/api/v1/dm.open` | open |
| POST | `/api/v1/dm.setTopic` | setTopic |

## im

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/im.blockUser` | blockUser |
| POST | `/api/v1/im.close` | close |
| GET | `/api/v1/im.counters` | counters |
| POST | `/api/v1/im.create` | create |
| POST | `/api/v1/im.delete` | delete |
| GET | `/api/v1/im.files` | files |
| GET | `/api/v1/im.history` | history |
| POST | `/api/v1/im.leave` | leave |
| GET | `/api/v1/im.list` | list |
| GET | `/api/v1/im.list.everyone` | list.everyone |
| GET | `/api/v1/im.members` | members |
| GET | `/api/v1/im.messages` | messages |
| GET | `/api/v1/im.messages.others` | messages.others |
| POST | `/api/v1/im.open` | open |
| POST | `/api/v1/im.setTopic` | setTopic |

## video-conference

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/video-conference.add-participants` | add-participants |
| POST | `/api/v1/video-conference.cancel` | cancel |
| GET | `/api/v1/video-conference.capabilities` | capabilities |
| POST | `/api/v1/video-conference.decline` | decline |
| POST | `/api/v1/video-conference.heartbeat` | heartbeat |
| GET | `/api/v1/video-conference.info` | info |
| POST | `/api/v1/video-conference.join` | join |
| GET | `/api/v1/video-conference.joinable` | joinable |
| POST | `/api/v1/video-conference.leave` | leave |
| GET | `/api/v1/video-conference.list` | list |
| GET | `/api/v1/video-conference.providers` | providers |
| POST | `/api/v1/video-conference.rename` | rename |
| POST | `/api/v1/video-conference.ring` | ring |
| POST | `/api/v1/video-conference.share-chat` | share-chat |
| POST | `/api/v1/video-conference.start` | start |

## e2e

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/e2e.acceptSuggestedGroupKey` | acceptSuggestedGroupKey |
| GET | `/api/v1/e2e.fetchMyKeys` | fetchMyKeys |
| GET | `/api/v1/e2e.fetchUsersWaitingForGroupKey` | fetchUsersWaitingForGroupKey |
| GET | `/api/v1/e2e.getUsersOfRoomWithoutKey` | getUsersOfRoomWithoutKey |
| POST | `/api/v1/e2e.provideUsersSuggestedGroupKeys` | provideUsersSuggestedGroupKeys |
| POST | `/api/v1/e2e.rejectSuggestedGroupKey` | rejectSuggestedGroupKey |
| POST | `/api/v1/e2e.requestSubscriptionKeys` | requestSubscriptionKeys |
| POST | `/api/v1/e2e.resetRoomKey` | resetRoomKey |
| POST | `/api/v1/e2e.setRoomKeyID` | setRoomKeyID |
| POST | `/api/v1/e2e.setUserPublicAndPrivateKeys` | setUserPublicAndPrivateKeys |
| POST | `/api/v1/e2e.updateGroupKey` | updateGroupKey |

## cloud

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/cloud.checkoutUrl` | checkoutUrl |
| GET | `/api/v1/cloud.confirmationPoll` | confirmationPoll |
| POST | `/api/v1/cloud.connectWorkspace` | connectWorkspace |
| POST | `/api/v1/cloud.createRegistrationIntent` | createRegistrationIntent |
| POST | `/api/v1/cloud.manualRegister` | manualRegister |
| POST | `/api/v1/cloud.registerPreIntent` | registerPreIntent |
| GET | `/api/v1/cloud.registrationStatus` | registrationStatus |
| POST | `/api/v1/cloud.removeLicense` | removeLicense |
| POST | `/api/v1/cloud.syncWorkspace` | syncWorkspace |
| GET | `/api/v1/cloud.workspaceRegisterData` | workspaceRegisterData |

## moderation

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/moderation.dismissReports` | dismissReports |
| POST | `/api/v1/moderation.dismissUserReports` | dismissUserReports |
| GET | `/api/v1/moderation.reportInfo` | reportInfo |
| POST | `/api/v1/moderation.reportUser` | reportUser |
| GET | `/api/v1/moderation.reports` | reports |
| GET | `/api/v1/moderation.reportsByUsers` | reportsByUsers |
| POST | `/api/v1/moderation.user.deleteReportedMessages` | user.deleteReportedMessages |
| GET | `/api/v1/moderation.user.reportedMessages` | user.reportedMessages |
| GET | `/api/v1/moderation.user.reportsByUserId` | user.reportsByUserId |
| GET | `/api/v1/moderation.userReports` | userReports |

## engagement-dashboard

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/engagement-dashboard/channels/list` | channels/list |
| GET | `/api/v1/engagement-dashboard/messages/messages-sent` | messages/messages-sent |
| GET | `/api/v1/engagement-dashboard/messages/origin` | messages/origin |
| GET | `/api/v1/engagement-dashboard/messages/top-five-popular-channels` | messages/top-five-popular-channels |
| GET | `/api/v1/engagement-dashboard/users/active-users` | users/active-users |
| GET | `/api/v1/engagement-dashboard/users/chat-busier/hourly-data` | users/chat-busier/hourly-data |
| GET | `/api/v1/engagement-dashboard/users/chat-busier/weekly-data` | users/chat-busier/weekly-data |
| GET | `/api/v1/engagement-dashboard/users/new-users` | users/new-users |
| GET | `/api/v1/engagement-dashboard/users/users-by-time-of-the-day-in-a-week` | users/users-by-time-of-the-day-in-a-week |

## roles

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/roles.addUserToRole` | addUserToRole |
| POST | `/api/v1/roles.create` | create |
| POST | `/api/v1/roles.delete` | delete |
| GET | `/api/v1/roles.getUsersInPublicRoles` | getUsersInPublicRoles |
| GET | `/api/v1/roles.getUsersInRole` | getUsersInRole |
| GET | `/api/v1/roles.list` | list |
| POST | `/api/v1/roles.removeUserFromRole` | removeUserFromRole |
| GET | `/api/v1/roles.sync` | sync |
| POST | `/api/v1/roles.update` | update |

## settings

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/settings` | (root) |
| POST | `/api/v1/settings` | (root) |
| POST | `/api/v1/settings.addCustomOAuth` | addCustomOAuth |
| GET | `/api/v1/settings.oauth` | oauth |
| GET | `/api/v1/settings.public` | public |
| POST | `/api/v1/settings.refreshOAuthServices` | refreshOAuthServices |
| POST | `/api/v1/settings.removeCustomOAuth` | removeCustomOAuth |
| GET | `/api/v1/settings/:_id` | :_id |
| POST | `/api/v1/settings/:_id` | :_id |

## integrations

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/integrations.clearHistory` | clearHistory |
| POST | `/api/v1/integrations.create` | create |
| GET | `/api/v1/integrations.get` | get |
| GET | `/api/v1/integrations.history` | history |
| GET | `/api/v1/integrations.list` | list |
| POST | `/api/v1/integrations.remove` | remove |
| POST | `/api/v1/integrations.replayOutgoing` | replayOutgoing |
| PUT | `/api/v1/integrations.update` | update |

## calendar-events

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/calendar-events.create` | create |
| POST | `/api/v1/calendar-events.delete` | delete |
| POST | `/api/v1/calendar-events.import` | import |
| GET | `/api/v1/calendar-events.info` | info |
| GET | `/api/v1/calendar-events.list` | list |
| POST | `/api/v1/calendar-events.update` | update |

## canned-responses

| Method | Endpoint | Action |
|---|---|---|
| DELETE | `/api/v1/canned-responses` † | (root) |
| GET | `/api/v1/canned-responses` † | (root) |
| POST | `/api/v1/canned-responses` † | (root) |
| GET | `/api/v1/canned-responses.get` † | get |
| DELETE | `/api/v1/canned-responses/:_id` † | :_id |
| GET | `/api/v1/canned-responses/:_id` † | :_id |

## email-inbox

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/email-inbox` | (root) |
| GET | `/api/v1/email-inbox.list` | list |
| GET | `/api/v1/email-inbox.search` | search |
| POST | `/api/v1/email-inbox.send-test/:_id` | send-test |
| DELETE | `/api/v1/email-inbox/:_id` | :_id |
| GET | `/api/v1/email-inbox/:_id` | :_id |

## sessions

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/sessions/info` | info |
| GET | `/api/v1/sessions/info.admin` | info.admin |
| GET | `/api/v1/sessions/list` | list |
| GET | `/api/v1/sessions/list.all` | list.all |
| POST | `/api/v1/sessions/logout` | logout |
| POST | `/api/v1/sessions/logout.me` | logout.me |

## audit

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/audit.auditions` | auditions |
| POST | `/api/v1/audit.messages` | messages |
| POST | `/api/v1/audit.omnichannelMessages` | omnichannelMessages |
| GET | `/api/v1/audit.settings` | settings |
| GET | `/api/v1/audit/rooms.members` | rooms.members |

## commands

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/commands.get` | get |
| GET | `/api/v1/commands.list` | list |
| GET | `/api/v1/commands.preview` | preview |
| POST | `/api/v1/commands.preview` | preview |
| POST | `/api/v1/commands.run` | run |

## custom-sounds

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/custom-sounds.create` | create |
| POST | `/api/v1/custom-sounds.delete` | delete |
| GET | `/api/v1/custom-sounds.getOne` | getOne |
| GET | `/api/v1/custom-sounds.list` | list |
| POST | `/api/v1/custom-sounds.update` | update |

## emoji-custom

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/emoji-custom.all` | all |
| POST | `/api/v1/emoji-custom.create` | create |
| POST | `/api/v1/emoji-custom.delete` | delete |
| GET | `/api/v1/emoji-custom.list` | list |
| POST | `/api/v1/emoji-custom.update` | update |

## import

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/import.addUsers` | addUsers |
| POST | `/api/v1/import.clear` | clear |
| POST | `/api/v1/import.new` | new |
| POST | `/api/v1/import.run` | run |
| GET | `/api/v1/import.status` | status |

## oauth-apps

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/oauth-apps.create` | create |
| POST | `/api/v1/oauth-apps.delete` | delete |
| GET | `/api/v1/oauth-apps.get` | get |
| GET | `/api/v1/oauth-apps.list` | list |
| POST | `/api/v1/oauth-apps.update` | update |

## push

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/push.get` | get |
| GET | `/api/v1/push.info` | info |
| POST | `/api/v1/push.test` | test |
| DELETE | `/api/v1/push.token` | token |
| POST | `/api/v1/push.token` | token |

## autotranslate

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/autotranslate.getProviderUiMetadata` | getProviderUiMetadata |
| GET | `/api/v1/autotranslate.getSupportedLanguages` | getSupportedLanguages |
| POST | `/api/v1/autotranslate.saveSettings` | saveSettings |
| POST | `/api/v1/autotranslate.translateMessage` | translateMessage |

## custom-user-status

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/custom-user-status.create` | create |
| POST | `/api/v1/custom-user-status.delete` | delete |
| GET | `/api/v1/custom-user-status.list` | list |
| POST | `/api/v1/custom-user-status.update` | update |

## experimental

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/experimental/login` † | login |
| GET | `/api/experimental/logout` † | logout |
| POST | `/api/experimental/logout` † | logout |
| POST | `/api/experimental/rooms.setCategory` | rooms.setCategory |

## licenses

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/licenses.add` | add |
| GET | `/api/v1/licenses.info` | info |
| GET | `/api/v1/licenses.maxActiveUsers` | maxActiveUsers |
| POST | `/api/v1/licenses.validate` | validate |

## media-calls

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/media-calls.answer` | answer |
| GET | `/api/v1/media-calls.info` | info |
| GET | `/api/v1/media-calls.state` | state |
| GET | `/api/v1/media-calls.stateSignals` | stateSignals |

## permissions

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/permissions.addRole` | addRole |
| GET | `/api/v1/permissions.listAll` | listAll |
| POST | `/api/v1/permissions.removeRole` | removeRole |
| POST | `/api/v1/permissions.update` | update |

## subscriptions

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/subscriptions.get` | get |
| GET | `/api/v1/subscriptions.getOne` | getOne |
| POST | `/api/v1/subscriptions.read` | read |
| POST | `/api/v1/subscriptions.unread` | unread |

## ai

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/ai.llm.models` | llm.models |
| GET | `/api/v1/ai.search` | search |
| POST | `/api/v1/ai.search.answer` | search.answer |

## banners

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/banners` | (root) |
| POST | `/api/v1/banners.dismiss` | dismiss |
| GET | `/api/v1/banners/:id` | :id |

## ldap

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/ldap.syncNow` | syncNow |
| POST | `/api/v1/ldap.testConnection` | testConnection |
| POST | `/api/v1/ldap.testSearch` | testSearch |

## statistics

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/statistics` | (root) |
| GET | `/api/v1/statistics.list` | list |
| POST | `/api/v1/statistics.telemetry` | telemetry |

##

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api//docs/json` | docs/json |
| GET | `/api//info` | info |

## assets

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/assets.setAsset` | setAsset |
| POST | `/api/v1/assets.unsetAsset` | unsetAsset |

## call-history

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/call-history.info` | info |
| GET | `/api/v1/call-history.list` | list |

## logout

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/logout` † | (root) |
| POST | `/api/v1/logout` † | (root) |

## mailer

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/mailer` | (root) |
| POST | `/api/v1/mailer.unsubscribe` | unsubscribe |

## method

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/method.call/:method` | call |
| POST | `/api/v1/method.callAnon/:method` | callAnon |

## presence

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/presence.enableBroadcast` | enableBroadcast |
| GET | `/api/v1/presence.getConnections` | getConnections |

## twoFactorChallenges

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/twoFactorChallenges.sendEmailCode` † | sendEmailCode |
| POST | `/api/v1/twoFactorChallenges.verifyChallenge` † | verifyChallenge |

## webdav

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/webdav.getMyAccounts` | getMyAccounts |
| POST | `/api/v1/webdav.removeWebdavAccount` | removeWebdavAccount |

## directory

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/directory` | (root) |

## downloadPendingAvatars

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/downloadPendingAvatars` | (root) |

## downloadPendingFiles

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/downloadPendingFiles` | (root) |

## downloadPublicImportFile

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/downloadPublicImportFile` | (root) |

## federation

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/federation/matrixIds.verify` | matrixIds.verify |

## findOrCreateInvite

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/findOrCreateInvite` | (root) |

## fingerprint

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/fingerprint` | (root) |

## getCurrentImportOperation

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/getCurrentImportOperation` | (root) |

## getImportFileData

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/getImportFileData` | (root) |

## getImportProgress

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/getImportProgress` | (root) |

## getLatestImportOperations

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/getLatestImportOperations` | (root) |

## importers

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/importers.list` | list |

## instances

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/instances.get` | get |

## listInvites

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/listInvites` | (root) |

## login

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/login` † | (root) |

## loginCode

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/loginCode.redeem` | redeem |

## me

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/me` | (root) |

## pw

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/pw.getPolicy` | getPolicy |

## removeInvite

| Method | Endpoint | Action |
|---|---|---|
| DELETE | `/api/v1/removeInvite/:_id` | :_id |

## saml

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/saml.parseMetadata` | parseMetadata |

## sendInvitationEmail

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/sendInvitationEmail` | (root) |

## service

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/service.configurations` | configurations |

## setupWizard

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/setupWizard.parameters` | parameters |

## shield

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/shield.svg` | svg |

## smtp

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/smtp.check` | check |

## spotlight

| Method | Endpoint | Action |
|---|---|---|
| GET | `/api/v1/spotlight` | (root) |

## startImport

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/startImport` | (root) |

## uploadImportFile

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/uploadImportFile` | (root) |

## uploads

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/uploads.delete` | delete |

## useInviteToken

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/useInviteToken` | (root) |

## validateInviteToken

| Method | Endpoint | Action |
|---|---|---|
| POST | `/api/v1/validateInviteToken` | (root) |
