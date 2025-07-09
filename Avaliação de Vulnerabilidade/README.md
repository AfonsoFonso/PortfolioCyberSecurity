# Análise de Vulnerabilidades em Servidor de Banco de Dados Crítico (Exercício Fictício)

**Status:** Concluído | **Data:** 01 de julho de 2025

---

### Descrição do Projeto

Este projeto consiste em um exercício prático de avaliação de vulnerabilidades e análise de risco em um servidor de banco de dados fictício, porém crítico para as operações de uma empresa. O objetivo foi identificar as principais ameaças, avaliar os riscos associados e propor uma estratégia de remediação para proteger o ativo, seguindo frameworks reconhecidos pelo mercado.

O relatório completo da avaliação pode ser encontrado neste diretório: `Vulnerability assessment report.pdf`.

### Contexto do Cenário

O ativo avaliado foi um servidor de banco de dados estratégico para o negócio, com as seguintes características:

* **Hardware:** Processador de alta performance e 128GB de memória.
* **Sistema Operacional:** A versão mais recente do sistema operacional Linux.
* **Software:** Banco de Dados MySQL, essencial para as operações do negócio.
* **Rede:** Conexão de rede estável utilizando endereços IPv4.
* **Medidas de Segurança Iniciais:** Conexões criptografadas com SSL/TLS.

### Objetivos da Avaliação

O propósito principal foi proteger os três pilares da segurança da informação—Confidencialidade, Integridade e Disponibilidade (CIA)—dos dados hospedados no servidor. A indisponibilidade ou comprometimento deste ativo resultaria em impactos severos, como interrupção operacional, perdas financeiras e danos à reputação da empresa.

### Metodologia Utilizada

* **Framework de Análise:** A análise de risco foi guiada pela metodologia do **NIST SP 800-30 Rev. 1**.
* **Abordagem:** Foi utilizada uma abordagem de avaliação qualitativa, focada em identificar um conjunto diversificado de ameaças de alto impacto para fornecer uma visão holística dos riscos mais significativos para o negócio.
* **Escopo:** A avaliação focou nos controles de acesso atuais do sistema.

### Resumo dos Riscos Identificados

A avaliação identificou os seguintes cenários de ameaça e seus respectivos níveis de risco:

| Fonte da Ameaça | Evento da Ameaça | Nível de Risco |
| :--- | :--- | :---: |
| **Hacker** | Ataque DoS para interromper operações. | **9 (Alto)** |
| **Empresa Competidora** | Acesso a informações confidenciais por infiltração. | **3 (Baixo)** |
| **Usuário Privilegiado**| Alteração e exclusão de dados confidenciais. | **3 (Baixo)** |

### Estratégia de Remediação Proposta

Para mitigar os riscos identificados, foi recomendada uma estratégia de **defesa em profundidade**, com os seguintes controles de segurança em camadas:

* **Controle de Ameaças Internas:**
    * Implementação do **Princípio do Menor Privilégio (PoLP)** para limitar permissões.
    * Fortalecimento da estrutura de **AAA (Authentication, Authorization, Accounting)** para garantir registros robustos.
* **Controle de Acesso e Exfiltração de Dados:**
    * Aplicação de **Autenticação Multifator (MFA)** para todo acesso administrativo.
    * Implantação de um serviço de **mitigação de DDoS baseado em nuvem** para proteger contra interrupções de serviço.

### Habilidades Demonstradas

* **Análise de Risco e Frameworks:** Aplicação prática da metodologia do NIST SP 800-30.
* **Modelagem de Ameaças:** Identificação de fontes de ameaças relevantes (hackers, insiders, competidores) e seus possíveis impactos.
* **Conceitos de Segurança:** Aplicação de conceitos fundamentais como Defesa em Profundidade, Confidencialidade, Integridade e Disponibilidade (CIA), Princípio do Menor Privilégio e AAA.
* **Comunicação Técnica:** Elaboração de um relatório estruturado para apresentar riscos e recomendações de forma clara.

---
**Observação:** Este é um projeto de estudo e o cenário apresentado é inteiramente fictício, criado com o propósito de demonstrar minhas habilidades em avaliação de segurança.
