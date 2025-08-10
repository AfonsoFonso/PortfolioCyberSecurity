# Conteúdo de exemplo para o arquivo 'allow_list.txt':
# 192.168.1.1
# 10.0.0.1
# 172.16.0.1
# 192.168.1.5
# 10.0.0.5
# 172.16.0.5


# Define o nome do arquivo a ser modificado
import_file = "allow_list.txt"

# Lista de endereços IP que devem ser removidos
remove_list = ["10.0.0.1", "192.168.1.2"]

try:
    with open(import_file, 'r') as file:
        ip_addresses = file.read()
except FileNotFoundError:
    print(f"Erro: O arquivo '{import_file}' não foi encontrado. Por favor, crie o arquivo.")
    exit()

# O método .split() divide a string por espaços em branco, incluindo quebras de linha
ip_addresses = ip_addresses.split()

print("Lista de IPs antes da remoção:")
print(ip_addresses)
print("-" * 30)

for element in remove_list:
    # Verifica se o IP está na lista antes de tentar remover
    if element in ip_addresses:
        ip_addresses.remove(element)
        print(f"Removido: {element}")
    else:
        print(f"Não encontrado na lista: {element}")

print("-" * 30)
print("Lista de IPs após a remoção:")
print(ip_addresses)

# O .join() junta os elementos da lista com uma quebra de linha  entre eles
ip_addresses_string = "\n".join(ip_addresses)

# O modo 'w' (write) apaga o conteúdo antigo e escreve o novo
with open(import_file, 'w') as file:
    file.write(ip_addresses_string)

print("\nArquivo 'allow_list.txt' atualizado com sucesso!")

