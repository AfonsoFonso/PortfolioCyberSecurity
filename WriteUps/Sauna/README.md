# Sauna — HackTheBox Write-up

**Active Directory | Windows Server | Dificuldade: Easy**

🇬🇧 [English version](README.en.md)

---

## Sumário Executivo

Sauna é uma máquina Windows do HackTheBox que simula o Active Directory de um banco fictício (Egotistical Bank). O ponto de partida não foi uma falha técnica, e sim uma falha de processo: os nomes completos dos funcionários estavam publicados na própria página institucional do site, permitindo gerar uma wordlist de usuários prováveis e testar diretamente AS-REP Roasting sem nenhum acesso prévio ao domínio.

A partir do foothold obtido com essa credencial, uma ferramenta de enumeração local (winPEAS) revelou credenciais de AutoLogon configuradas em texto plano no registro, pertencentes a uma conta de serviço com os direitos estendidos `DS-Replication-Get-Changes` e `DS-Replication-Get-Changes-All` concedidos diretamente sobre o objeto do domínio — sem depender de nenhuma cadeia de grupos aninhados. Essa concessão direta de direitos de replicação é, por si só, suficiente para um DCSync completo.

## Informações da Máquina

| Atributo | Valor |
|---|---|
| Nome | Sauna |
| Plataforma | HackTheBox |
| Sistema Operacional | Windows Server (Active Directory) |
| Domínio | `EGOTISTICAL-BANK.LOCAL` |
| Dificuldade | Easy |
| Categoria | Active Directory |
| Técnicas principais | OSINT, geração de usernames, AS-REP Roasting, AutoLogon credentials, DCSync |

---

## 1. Reconhecimento

Scan inicial de portas e serviços com os scripts padrão do Nmap:

```bash
nmap -sC 10.129.36.152
```

![Varredura Nmap identificando um Domain Controller com um serviço web exposto](images/01_nmap.png)

Além da assinatura clássica de Domain Controller (Kerberos, LDAP, SMB), a porta 80 chamou atenção por hospedar um site institucional com o título "Egotistical Bank" — um detalhe que direcionou a investigação seguinte para o próprio conteúdo do site, e não apenas para os serviços de rede.

## 2. OSINT — Nomes de Funcionários no Próprio Site

A página "Meet the Team" do site expôs publicamente o nome completo de seis funcionários da organização fictícia:

![Página institucional expondo nomes completos da equipe](images/02_osint_team.png)

Esse é um padrão de vazamento de informação extremamente comum em ambientes corporativos reais: páginas de "Sobre Nós" ou "Nossa Equipe", pensadas para transmitir confiança a clientes, frequentemente entregam de graça o primeiro passo de qualquer ataque de força bruta de usuário — o nome completo de quem tem conta no domínio.

Como o formato exato do nome de usuário no domínio (login) não estava visível, o próximo passo foi gerar todas as variações plausíveis (primeiro nome, sobrenome, primeira letra + sobrenome, etc.) com a ferramenta `username-anarchy`:

```bash
./username-anarchy --input-file names.txt > usernames.txt
```

![Geração de variações de nome de usuário a partir dos nomes coletados](images/03_username_anarchy.png)

Essa etapa converte uma lista de nomes públicos em uma wordlist de credenciais candidatas — peça essencial quando não se tem acesso a nenhuma enumeração autenticada de usuários do domínio.

## 3. Acesso Inicial — AS-REP Roasting

Com a wordlist de usernames gerada, o próximo passo foi testar diretamente quais desses nomes prováveis existem no domínio e têm a pré-autenticação Kerberos desabilitada:

```bash
impacket-GetNPUsers EGOTISTICAL-BANK.LOCAL/ -no-pass -usersfile users.txt -dc-ip '10.129.36.152'
```

![Hash AS-REP obtido para o usuário fsmith em meio a dezenas de tentativas malsucedidas](images/04_asrep_attempt.png)

A grande maioria das variações geradas retornou `KDC_ERR_C_PRINCIPAL_UNKNOWN` — ou seja, não correspondem a contas reais —, mas `fsmith` (variação de Fergus Smith) existia e retornou um hash `$krb5asrep$23$`. O volume de tentativas malsucedidas não é um problema nessa técnica: é simplesmente o custo de não ter uma lista de usuários confirmada previamente.

O hash foi quebrado offline com John the Ripper:

```bash
john --format=krb5asrep --wordlist=/usr/share/wordlists/rockyou.txt fsmithhash.txt
```

![Senha de fsmith recuperada em 3 segundos](images/05_john_crack.png)

Senha recuperada: **`Thestrokes23`** — uma senha baseada em cultura pop (nome de banda), padrão comum o suficiente para estar presente em wordlists públicas como a rockyou.txt.

## 4. Flag de Usuário

Com as credenciais válidas, o acesso via WinRM foi direto:

```bash
evil-winrm -i 10.129.36.152 -u 'fsmith'
```

![Shell interativa como fsmith e primeira flag](images/06_user_flag.png)

## 5. Mapeamento do Domínio com BloodHound

```bash
bloodhound-python -u 'fsmith' -p 'Thestrokes23' -d EGOTISTICAL-BANK.LOCAL -ns 10.129.37.25 -c All
```

![Coleta de dados do domínio: 7 usuários, 52 grupos, 3 GPOs](images/07_bloodhound_collect.png)

O domínio coletado é pequeno (apenas 7 usuários), o que já é um indício de que a cadeia de privilégio provavelmente será curta e direta. Os dados foram coletados para análise posterior, em paralelo com a enumeração local na máquina.

## 6. Enumeração Local — Credenciais de AutoLogon

Com acesso via shell, o próximo passo foi rodar uma ferramenta de enumeração de privesc local. O winPEAS foi carregado na máquina e, entre suas verificações padrão, uma delas foi decisiva:

![winPEAS revela credenciais de AutoLogon armazenadas em texto plano no registro](images/08_winpeas_autologon.png)

O Windows permite configurar login automático de uma conta armazenando usuário e senha em texto plano em chaves do registro (`HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`) — um recurso pensado para conveniência operacional que, na prática, é uma das formas mais diretas de exposição de credencial em ambientes Windows. Aqui, a conta exposta foi `svc_loanmgr`, com a senha `Moneymakestheworldgoround!`. Vale notar que o próprio nome da conta ("gerente de empréstimos") mantém a consistência temática do cenário fictício do banco.

## 7. Análise de ACL — Direitos de Replicação Diretos

Voltando ao BloodHound com a nova credencial em mente, a busca pelo nó `svc_loanmgr` revelou que a conta tem as permissões `GetChanges` e `GetChangesAll` concedidas **diretamente** sobre o objeto do domínio, sem herança de grupo:

![BloodHound confirma GetChanges + GetChangesAll não herdados sobre EGOTISTICAL-BANK.LOCAL](images/09_bloodhound_acl.png)

Essa é uma variação importante de entender em ataques de ACL abuse: nem toda escalação para DCSync depende de uma cadeia de `GenericAll`/`WriteDacl` em vários elos — às vezes a permissão de replicação já está concedida diretamente a uma conta de serviço, geralmente por conveniência administrativa (contas de backup ou sincronização que legitimamente precisam ler todo o diretório). O próprio BloodHound já indica a exploração direta via mimikatz ou, no caso deste ataque, via `secretsdump` do Impacket.

## 8. DCSync e Comprometimento do Domínio

```bash
impacket-secretsdump EGOTISTICAL-BANK.LOCAL/svc_loanmgr:'Moneymakestheworldgoround!'@10.129.37.25
```

![Dump completo do NTDS.DIT via DRSUAPI, incluindo o hash do Administrator](images/10_secretsdump.png)

O domínio pequeno se confirma aqui: apenas `Administrator`, `Guest`, `krbtgt`, `HSmith`, `FSmith`, `svc_loanmgr` e a conta de máquina `SAUNA$`. O hash NTLM do Administrator (`823452073d75b9d1cf70ebdf86c7f98e`) foi extraído com sucesso.

## 9. Root Flag — Pass-the-Hash

```bash
evil-winrm -i 10.129.37.25 -u 'Administrator' -H '823452073d75b9d1cf70ebdf86c7f98e'
```

![Acesso como Administrator via Pass-the-Hash e flag final](images/11_root_flag.png)

---

## 10. Cadeia de Ataque — Resumo

1. Nmap identifica um Domain Controller (`EGOTISTICAL-BANK.LOCAL`) com um site institucional na porta 80.
2. A página "Meet the Team" do site expõe nomes completos de funcionários.
3. `username-anarchy` converte os nomes em uma wordlist de usernames prováveis.
4. AS-REP Roasting contra a wordlist revela que `fsmith` existe e tem pré-autenticação desabilitada.
5. Hash quebrado offline com John the Ripper (senha: `Thestrokes23`).
6. Acesso via WinRM como `fsmith` — primeira flag capturada.
7. winPEAS encontra credenciais de AutoLogon em texto plano no registro (`svc_loanmgr`).
8. BloodHound confirma que `svc_loanmgr` tem `GetChanges` + `GetChangesAll` diretamente sobre o domínio.
9. `secretsdump` executa o DCSync e extrai o hash do Administrator.
10. Pass-the-Hash finaliza o comprometimento total do domínio.

## 11. Lições Técnicas

- Páginas institucionais ("Sobre Nós", "Nossa Equipe") são uma fonte de OSINT subestimada: nomes completos publicados por marketing viram diretamente material de ataque de força bruta de usuário.
- Geração de usernames (`username-anarchy` ou equivalente) é uma técnica que compensa a ausência de enumeração autenticada — o custo de tentativas malsucedidas é baixo frente ao ganho de descobrir contas reais sem nenhum acesso prévio.
- AutoLogon armazenado em texto plano no registro é uma das formas mais diretas e ainda comuns de exposição de credencial em ambientes Windows — vale ser um dos primeiros itens verificados em qualquer enumeração local pós-shell.
- Nem toda escalação para DCSync passa por uma cadeia longa de ACL abuse: direitos de replicação concedidos diretamente a uma conta de serviço são igualmente críticos e frequentemente mais fáceis de passar despercebidos, por não aparecerem como uma cadeia visualmente óbvia.
- Domínios pequenos (poucos usuários e grupos) não significam superfície de ataque pequena — o domínio inteiro se resolve com apenas 7 usuários no AD.

## 12. Recomendações de Mitigação

- Revisar todo conteúdo público do site institucional antes de publicar — nomes completos de funcionários em páginas de marketing devem ser tratados como informação sensível do ponto de vista de segurança, não só de RH/comunicação.
- Nunca configurar AutoLogon com credenciais em texto plano no registro; se o recurso for estritamente necessário, usar Credential Guard ou LSA Protection para proteger o armazenamento.
- Auditar regularmente quais contas têm `DS-Replication-Get-Changes` e `DS-Replication-Get-Changes-All` concedidos diretamente (fora do grupo padrão de controladores de domínio) — esse tipo de concessão direta é fácil de esquecer depois de configurada.
- Monitorar chamadas DRSUAPI de origem que não seja um Domain Controller legítimo.
- Aplicar o mesmo rigor de rotação e complexidade de senha a contas de serviço que a contas humanas privilegiadas.

## Ferramentas Utilizadas

| Ferramenta | Finalidade |
|---|---|
| Nmap | Varredura de portas e detecção de serviços |
| username-anarchy | Geração de variações de nome de usuário a partir de nomes reais |
| Impacket (GetNPUsers, secretsdump) | AS-REP Roasting e extração de credenciais via DCSync |
| John the Ripper | Quebra de hash offline (AS-REP) |
| Evil-WinRM | Shell interativa via WinRM, incluindo Pass-the-Hash |
| BloodHound / bloodhound-python | Mapeamento de relações de privilégio no AD |
| winPEAS | Enumeração local de privesc no Windows |
