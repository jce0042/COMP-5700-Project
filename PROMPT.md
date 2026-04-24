# Zero-Shot Prompt

```
[INST]
Analyze the following security document and identify the key data elements (KDEs) and their corresponding requirements. For each KDE, provide a name and a list of requirements associated with it. Structure the output as a nested dictionary where each key is a KDE, and the value is another dictionary containing the 'name' of the KDE and a 'requirements' list.

Document:
{document_text}
[/INST]
```

# Few-Shot Prompt

```
[INST]
Analyze the following security document and identify the key data elements (KDEs) and their corresponding requirements. For each KDE, provide a name and a list of requirements associated with it. Structure the output as a nested dictionary where each key is a KDE, and the value is another dictionary containing the 'name' of the KDE and a 'requirements' list.

Here are some examples:

Example 1:
Document: "The system shall enforce password complexity. Passwords must be at least 8 characters long and contain a mix of uppercase, lowercase, and numeric characters."
Output:
{
  "password_complexity": {
    "name": "Password Complexity",
    "requirements": [
      "at least 8 characters long",
      "contain a mix of uppercase, lowercase, and numeric characters"
    ]
  }
}

Example 2:
Document: "All sensitive data must be encrypted at rest using AES-256. Access to encrypted data should be logged."
Output:
{
  "data_encryption": {
    "name": "Data Encryption",
    "requirements": [
      "encrypted at rest using AES-256"
    ]
  },
  "access_logging": {
    "name": "Access Logging",
    "requirements": [
      "Access to encrypted data should be logged"
    ]
  }
}

Now, analyze the following document:

Document:
{document_text}
[/INST]
```

# Chain-of-Thought Prompt

```
[INST]
Analyze the following security document and identify the key data elements (KDEs) and their corresponding requirements. First, think step-by-step about how to identify the KDEs and their requirements. Second, for each KDE, provide a name and a list of requirements associated with it. Finally, structure the output as a nested dictionary where each key is a KDE, and the value is another dictionary containing the 'name' of the KDE and a 'requirements' list.

Document:
{document_text}
[/INST]
```
